from django.dispatch import receiver
from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from .models import Order
from enrollments.models import UserEnrollment

@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    ipn_obj = sender
    if ipn_obj.payment_status == ST_PP_COMPLETED:
        try:
            # We used order.transaction_id as the 'invoice'
            order = Order.objects.get(transaction_id=ipn_obj.invoice)
            
            # Verify amount to prevent tampering
            if float(order.total_amount) == float(ipn_obj.mc_gross):
                order.status = Order.OrderStatus.PAID
                order.save()
                
                # Enroll User
                item = order.items.first().item
                UserEnrollment.objects.get_or_create(user=order.user, item=item, source_order=order)
                print(f"PayPal IPN Success: Order {order.transaction_id}")
        except Order.DoesNotExist:
            print("PayPal IPN Error: Order not found")