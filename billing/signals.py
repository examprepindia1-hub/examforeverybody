from django.dispatch import receiver
from paypal.standard.models import ST_PP_COMPLETED,ST_PP_DENIED, ST_PP_FAILED
from paypal.standard.ipn.signals import valid_ipn_received
from .models import Order
from enrollments.models import UserEnrollment
from paypal.standard.ipn.signals import invalid_ipn_received
@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    ipn_obj = sender
    
    # 1. Get the Order
    try:
        order = Order.objects.get(transaction_id=ipn_obj.invoice)
    except Order.DoesNotExist:
        print(f"IPN ERROR: Order {ipn_obj.invoice} not found")
        return

    # 2. Handle SUCCESS
    if ipn_obj.payment_status == ST_PP_COMPLETED:
        if float(order.total_amount) == float(ipn_obj.mc_gross):
            order.status = Order.OrderStatus.PAID
            order.payment_method = 'PAYPAL'
            order.external_transaction_id = ipn_obj.txn_id
            order.save()
            
            # Enroll User
            item = order.items.first().item
            UserEnrollment.objects.get_or_create(user=order.user, item=item, source_order=order)
            print(f"SUCCESS: Order {order.transaction_id} Paid")
        else:
            print("FRAUD: Amount mismatch")
            order.status = Order.OrderStatus.FAILED
            order.save()

    # 3. Handle FAILURE (Insufficient Funds / Denied)
    elif ipn_obj.payment_status in [ST_PP_DENIED, ST_PP_FAILED]:
        print(f"PAYMENT FAILED: {ipn_obj.payment_status} for Order {order.transaction_id}")
        
        # Mark order as Failed
        order.status = Order.OrderStatus.FAILED
        order.save()
        
        # OPTIONAL: Revoke access if they were already enrolled (e.g. eCheck bounce)
        UserEnrollment.objects.filter(source_order=order).delete()

@receiver(invalid_ipn_received)
def invalid_ipn_trigger(sender, **kwargs):
    ipn_obj = sender
    print(f"INVALID IPN RECEIVED: {ipn_obj.payment_status} - {ipn_obj.invoice}")
    # This means PayPal talked to us, but the verification failed (mismatched emails, settings, etc.)