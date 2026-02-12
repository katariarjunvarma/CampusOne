from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import PreOrder


@receiver(post_save, sender=PreOrder)
def send_ready_email(sender, instance, created, **kwargs):
    """Send email notification when order status changes to 'ready'"""
    if not created and instance.status == PreOrder.STATUS_READY and not instance.email_sent:
        user = instance.ordered_by
        if user and user.email:
            subject = f"Your Food Order #{instance.order_number} is Ready for Pickup"
            message = f"""Hello {user.first_name or user.username},

Your food order is now ready for pickup!

Order Details:
- Order Number: {instance.order_number}
- Item: {instance.food_item.name}
- Stall: {instance.food_item.stall_name}
- Location: {instance.food_item.location}
- Quantity: {instance.quantity}
- Break Slot: {instance.slot.name}

Please collect your order from the stall during your selected break slot.

Thank you,
SmartLPU Food Pre-Order System
"""
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                instance.email_sent = True
                instance.save(update_fields=['email_sent'])
            except Exception:
                pass
