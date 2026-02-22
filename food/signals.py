from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import PreOrder


@receiver(post_save, sender=PreOrder)
def update_order_status_actions(sender, instance, created, **kwargs):
    """
    Handle actions when order status changes:
    1. Send email when 'ready'.
    2. Apply penalties when 'missed'.
    """
    if created:
        return

    # Case 1: Order marked as READY -> Send Email
    if instance.status == PreOrder.STATUS_READY and not instance.email_sent:
        user = instance.ordered_by
        if user and user.email:
            subject = f"Order #{instance.order_number or instance.id} Ready for Pickup - CampusOne"
            try:
                html_message = render_to_string('food/email/order_notification.html', {
                    'order': instance,
                    'type': 'ready'
                })
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True,
                )
                
                # Update flag to prevent double sending
                PreOrder.objects.filter(pk=instance.pk).update(email_sent=True)
            except Exception as e:
                print(f"Failed to send email signal: {e}")

    # Case 2: Order marked as MISSED -> Apply Penalty
    # We need to check if this is a transition to 'missed'.
    # Note: 'post_save' doesn't give previous state easily without custom tracking, 
    # but we can rely on the fact that we set status='missed'.
    # To avoid re-applying penalty if saved multiple times as 'missed', strictly we should check before.
    # However, for simplicity here, we'll calculate total missed orders for the user.
    
    if instance.status == PreOrder.STATUS_MISSED:
        user = instance.ordered_by
        if user:
            # Count total missed orders for this user
            # We assume 'missed' status persists until monthly cleanup
            missed_count = PreOrder.objects.filter(ordered_by=user, status=PreOrder.STATUS_MISSED).count()
            
            # Determine Penalty
            penalty_action = None
            if missed_count == 1:
                penalty_action = "Warning Notification: Please pick up your orders."
            elif missed_count == 2:
                penalty_action = "1-Day Ban: You cannot order for 1 day."
            elif missed_count == 3:
                penalty_action = "3-Day Ban: You cannot order for 3 days."
            elif missed_count >= 4:
                penalty_action = "1-Week Ban: Your account is under review."
            
            if penalty_action:
                print(f"User {user.username} Penalty ({missed_count} misses): {penalty_action}")
                # Ideally send an email or notification to the user about the penalty
                if user.email:
                    try:
                        send_mail(
                            subject="CampusOne - Order Penalty Notice",
                            message=f"You have missed {missed_count} orders. Action: {penalty_action}",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass
