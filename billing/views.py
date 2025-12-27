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
from django.urls import reverse

# Django-PayPal Imports
from paypal.standard.forms import PayPalPaymentsForm

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from billing.models import Order, OrderItem
from billing.utils import generate_upi_qr_image

@csrf_exempt
@login_required
def check_payment_status(request, order_id):
    """
    Called periodically by JS to check if Order.status has changed to PAID.
    """
    try:
        order = Order.objects.get(transaction_id=order_id, user=request.user)
        return JsonResponse({'status': order.status})
    except Order.DoesNotExist:
        return JsonResponse({'status': 'UNKNOWN'}, status=404)

@csrf_exempt
@login_required
def expire_order(request, order_id):
    """
    Called by JS after timeout.
    """
    if request.method == "POST":
        try:
            order = Order.objects.get(transaction_id=order_id, user=request.user)
            if order.status == Order.OrderStatus.PENDING:
                order.status = Order.OrderStatus.FAILED
                order.save()
                return JsonResponse({'status': 'FAILED'})
            return JsonResponse({'status': order.status})
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
    if not getattr(settings, 'PAYMENTS_ACTIVE', True):
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    total_amount=0,
                    status=Order.OrderStatus.PAID,
                    payment_method='BETA_WAIVER',
                    transaction_id=f"BETA-{uuid.uuid4().hex[:8]}"
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
        # 3. REAL PAYMENT MODE (PayPal Standard + UPI)
        
        # A. Create a Pending Order Reference for PayPal
        # We need this ID to put in the 'invoice' field so we know who paid later
        order, created = Order.objects.get_or_create(
            user=request.user,
            items__item=item,
            status=Order.OrderStatus.PENDING,
            defaults={
                'total_amount': item.price,
                'transaction_id': f"PP-{uuid.uuid4().hex[:12].upper()}"
            }
        )
        
        # Ensure OrderItem exists
        if created:
            OrderItem.objects.create(order=order, item=item, price_at_purchase=item.price)

        # B. Configure PayPal Form
        host = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        
        paypal_dict = {
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "amount": str(item.price),
            "item_name": item.title,
            "invoice": order.transaction_id, # Crucial: Links payment to this order
            "currency_code": getattr(settings, 'PAYPAL_CURRENCY', 'USD'),
            "notify_url": f"{protocol}://{host}{reverse('paypal-ipn')}",
            "return": f"{protocol}://{host}{reverse('marketplace:item_detail', args=[item.slug])}",
            "cancel_return": f"{protocol}://{host}{reverse('marketplace:item_detail', args=[item.slug])}",
        }

        # Create the form instance
        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        context = {
            'item': item,
            'paypal_form': paypal_form, # Pass the form to template
            'paypal_currency': getattr(settings, 'PAYPAL_CURRENCY', 'USD') 
        }
        return render(request, 'billing/payment_page.html', context)

# --- Removed create_paypal_order and capture_paypal_order (Not needed for Standard IPN) ---

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
                    transaction_id=f"UPI-{uuid.uuid4().hex[:12].upper()}"
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