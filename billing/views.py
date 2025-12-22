import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.core.files.base import ContentFile

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from billing.models import Order, OrderItem
from billing.paypal_client import PayPalClient 
from billing.utils import generate_upi_qr_image
from django.utils import timezone

@csrf_exempt
@login_required
def check_payment_status(request, order_id):
    """
    Called periodically by JS to check if Order.status has changed to PAID.
    Uses transaction_id to find the order.
    """
    try:
        # Use transaction_id because that's what we expose to the frontend
        order = Order.objects.get(transaction_id=order_id, user=request.user)
        return JsonResponse({'status': order.status})
    except Order.DoesNotExist:
        return JsonResponse({'status': 'UNKNOWN'}, status=404)

@csrf_exempt
@login_required
def expire_order(request, order_id):
    """
    Called by JS after 4 minutes timeout.
    Marks the order as FAILED if it is still PENDING.
    """
    if request.method == "POST":
        try:
            order = Order.objects.get(transaction_id=order_id, user=request.user)
            if order.status == Order.OrderStatus.PENDING:
                order.status = Order.OrderStatus.FAILED
                order.save()
                return JsonResponse({'status': 'FAILED'})
            return JsonResponse({'status': order.status}) # Return actual status if not pending
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required
def initiate_purchase(request, slug):
    item = get_object_or_404(MarketplaceItem, slug=slug)
    
    # 1. Check if already enrolled
    if UserEnrollment.objects.filter(user=request.user, item=item).exists():
        messages.info(request, "You are already enrolled in this content.")
        return redirect('marketplace:item_detail', slug=slug)

    # 2. Beta / Dev Mode (Bypasses Payment if configured)
    if not settings.PAYMENTS_ACTIVE:
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    total_amount=0,
                    status=Order.OrderStatus.PAID,
                    payment_method='BETA_WAIVER',
                    transaction_id='beta_access'
                )
                OrderItem.objects.create(order=order, item=item, price_at_purchase=item.price)
                UserEnrollment.objects.create(user=request.user, item=item, source_order=order)
                
            messages.success(request, f"Welcome aboard! You've enrolled in {item.title}.")
            return redirect('marketplace:item_detail', slug=slug)

        except Exception as e:
            messages.error(request, "Enrollment failed.")
            print(f"Beta Enrollment Error: {e}")
            return redirect('marketplace:item_detail', slug=slug)

    else:
        # 3. REAL PAYMENT MODE (PayPal + UPI)
        context = {
            'item': item,
            'paypal_client_id': settings.PAYPAL_CLIENT_ID,
            # CRITICAL FIX: Pass currency to template so buttons render correctly
            'paypal_currency': getattr(settings, 'PAYPAL_CURRENCY', 'USD') 
        }
        return render(request, 'billing/payment_page.html', context)

@csrf_exempt
@login_required
def create_paypal_order(request):
    """
    Called by JS when user clicks 'PayPal' button.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            slug = data.get('slug')
            item = get_object_or_404(MarketplaceItem, slug=slug)
            
            # Initialize Client
            paypal = PayPalClient()
            
            # CRITICAL FIX: Use the currency from settings, do not hardcode USD
            currency_code = getattr(settings, 'PAYPAL_CURRENCY', 'USD')
            
            pp_response = paypal.create_order(amount=item.price, currency=currency_code) 
            
            if 'id' not in pp_response:
                return JsonResponse({'error': f"PayPal API Error: {pp_response}"}, status=400)

            pp_order_id = pp_response['id']
            
            # Create Local Pending Order
            order = Order.objects.create(
                user=request.user,
                total_amount=item.price,
                status=Order.OrderStatus.PENDING,
                payment_method='PAYPAL',
                transaction_id=pp_order_id
            )
            
            OrderItem.objects.create(order=order, item=item, price_at_purchase=item.price)
            
            return JsonResponse({'id': pp_order_id})
            
        except Exception as e:
            print(f"Create PayPal Order Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)

@csrf_exempt
@login_required
def capture_paypal_order(request):
    """
    Called by JS after user approves payment on PayPal popup.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            pp_order_id = data.get('orderID')
            
            paypal = PayPalClient()
            
            # 1. Verify with PayPal
            capture_data = paypal.capture_order(pp_order_id)
            
            if capture_data.get('status') == 'COMPLETED':
                # 2. Find local order
                order = Order.objects.get(transaction_id=pp_order_id)
                
                with transaction.atomic():
                    # 3. Update Order Status
                    order.status = Order.OrderStatus.PAID
                    order.save()
                    
                    # 4. Enroll the User
                    order_item = order.items.first() 
                    if not UserEnrollment.objects.filter(user=order.user, item=order_item.item).exists():
                        UserEnrollment.objects.create(
                            user=order.user,
                            item=order_item.item,
                            source_order=order
                        )
                
                return JsonResponse({'status': 'COMPLETED'})
            
            else:
                return JsonResponse({'error': 'Payment not completed'}, status=400)

        except Exception as e:
            print(f"Capture PayPal Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)

@csrf_exempt
@login_required
def create_upi_order(request):
    """
    Generates QR code for UPI payments.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            slug = data.get('slug')
            customer_vpa = data.get('upi_id')
            
            item = get_object_or_404(MarketplaceItem, slug=slug)
            
            with transaction.atomic():
                # 1. Create Order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=item.price,
                    status=Order.OrderStatus.PENDING,
                    payment_method='UPI',
                    payer_upi_id=customer_vpa,
                    transaction_id=f"ORD-{uuid.uuid4().hex[:8].upper()}"
                )
                
                OrderItem.objects.create(order=order, item=item, price_at_purchase=item.price)
                
                # 2. Generate QR
                qr_blob = generate_upi_qr_image(
                    order_id=order.transaction_id,
                    amount=item.price,
                    merchant_vpa=settings.UPI_MERCHANT_VPA,
                    merchant_name=settings.UPI_MERCHANT_NAME
                )
                
                # 3. Save QR to Order
                filename = f"qr_{order.transaction_id}.png"
                order.qr_code.save(filename, ContentFile(qr_blob.getvalue()), save=True)
                
            return JsonResponse({
                'qr_url': order.qr_code.url,
                'order_ref': order.transaction_id,
                'amount': str(order.total_amount)
            })
            
        except Exception as e:
            print(f"UPI Order Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created').prefetch_related('items__item')
    return render(request, 'billing/order_history.html', {'orders': orders})