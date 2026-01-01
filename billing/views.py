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
                order.status = Order.OrderStatus.TIMED_OUT
                order.save()
                return JsonResponse({'status': 'TIMED_OUT'})
            return JsonResponse({'status': order.status})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=400)



# --- NEW: Success/Cancel Views ---
@login_required
def payment_success(request):
    """
    Displays a professional success receipt and redirects user.
    """
    txn_id = request.GET.get('order_id')
    
    # Security: Ensure the order exists and belongs to this user
    order = get_object_or_404(Order, transaction_id=txn_id, user=request.user)
    
    # Get the item for the redirect button
    item = order.items.first().item
    next_url = reverse('marketplace:item_detail', args=[item.slug])

    context = {
        'order': order,
        'item': item,
        'next_url': next_url
    }
    return render(request, 'billing/payment_success.html', context)
    

@login_required
def payment_cancel(request):
    """
    Displays a professional failure/cancellation receipt.
    """
    txn_id = request.GET.get('order_id')
    
    # Try to find the order to show details (Amount, Title)
    # Using filter().first() instead of 404 so we can show a generic error if ID is missing
    order = Order.objects.filter(transaction_id=txn_id, user=request.user).first()
    
    context = {'order': order}
    
    if order:
        # Pass the item so the 'Try Again' button knows where to go
        context['item'] = order.items.first().item
        
    return render(request, 'billing/payment_pending.html', context)

@login_required
def initiate_purchase(request, slug):
    item = get_object_or_404(MarketplaceItem, slug=slug)
    
    # 1. Check if already enrolled
    if UserEnrollment.objects.filter(user=request.user, item=item).exists():
        messages.info(request, "You are already enrolled in this content.")
        return redirect('marketplace:item_detail', slug=slug)

    usd_price = item.price_usd  # Assuming ~86 INR = 1 USD
    

    # B. Create Pending Order
    # Note: We save the USD price in total_amount so it matches PayPal's return signal
    with transaction.atomic():
                # 1. Create Order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=usd_price,
                    currency='USD',
                    status=Order.OrderStatus.PENDING,
                    payment_method='PAYPAL',
                    payer_upi_id=None,
                    transaction_id=f"PAYPAL-{uuid.uuid4().hex[:12].upper()}"
                )
                
                OrderItem.objects.create(order=order, item=item, price_at_purchase=usd_price)

    # C. Configure PayPal Form
    host = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    
    success_url = f"{protocol}://{host}{reverse('payment_success')}?order_id={order.transaction_id}"
    cancel_url = f"{protocol}://{host}{reverse('payment_cancel')}?order_id={order.transaction_id}"
    paypal_dict = {
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": str(usd_price), # Sending USD amount
        "item_name": item.title,
        "invoice": order.transaction_id,
        "currency_code": "USD", # Force USD
        
        # Where PayPal sends the invisible success signal (Must be public internet URL)
        "notify_url": f"{protocol}://{host}{reverse('paypal-ipn')}",
        
        # Where User is redirected after payment
       "return": success_url,
        
        # Where User is redirected if they cancel
        "cancel_return": cancel_url,
    }

    # Create the form instance
    paypal_form = PayPalPaymentsForm(initial=paypal_dict)

    context = {
        'item': item,
        'paypal_form': paypal_form,
        'usd_price': usd_price # Pass this to show user approx USD cost
    }
    return render(request, 'billing/payment_page.html', context)

# ... (Keep your existing create_upi_order, check_payment_status, order_history views) ...
# Ensure to copy your existing UPI/Polling views here.
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
                    currency='INR',
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