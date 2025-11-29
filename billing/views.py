from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from billing.models import Order, OrderItem

@login_required
def initiate_purchase(request, slug):
    item = get_object_or_404(MarketplaceItem, slug=slug)
    
    # 1. Check if already enrolled (Prevent duplicate purchase)
    if UserEnrollment.objects.filter(user=request.user, item=item).exists():
        messages.info(request, "You are already enrolled in this content.")
        return redirect('item_detail', slug=slug)

    # 2. Logic Branch based on Payment Flag
    if not settings.PAYMENTS_ACTIVE:
        # ============================================================
        # PATH A: BETA / DEV MODE (Simulate a full purchase for ₹0)
        # ============================================================
        
        try:
            with transaction.atomic():
                # A. Create the "Order" record (Status: PAID immediately)
                order = Order.objects.create(
                    user=request.user,
                    total_amount=0,  # Free
                    status=Order.OrderStatus.PAID,
                    payment_method='BETA_WAIVER',
                    transaction_id='beta_access'
                )

                # B. Create the "Line Item"
                OrderItem.objects.create(
                    order=order,
                    item=item,
                    price_at_purchase=item.price  # Store original price for analytics
                )

                # C. Generate the "Ticket" (Enrollment) linked to the Order
                UserEnrollment.objects.create(
                    user=request.user,
                    item=item,
                    source_order=order
                )
                
            messages.success(request, f"Welcome aboard! You've enrolled in {item.title}.")
            # Redirect to dashboard or content page (Update 'home' to your actual dashboard URL later)
            return  redirect('marketplace:item_detail', slug=slug)

        except Exception as e:
            messages.error(request, "Something went wrong during enrollment. Please try again.")
            print(f"Enrollment Error: {e}")
            return redirect('marketplace:item_detail', slug=slug)

    else:
        # ============================================================
        # PATH B: RAZORPAY MODE (Real Payment)
        # ============================================================
        # This will be enabled later. For now, we prepare the data.
        
        amount_in_paise = int(item.price * 100)
        
        # TODO: Initialize Razorpay Client Here
        # client = razorpay.Client(...)
        # payment = client.order.create(...)

        context = {
            'item': item,
            'razorpay_order_id': 'order_dummy_123', # Placeholder
            'amount': amount_in_paise,
            'key_id': settings.RAZORPAY_KEY_ID
        }
        return render(request, 'billing/payment_page.html', context)