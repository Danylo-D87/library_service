from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe
import logging

from borrowings.models import Borrowing
from config.notifications.tasks import send_telegram_payment_notification
from .models import Payment
from .serializers import PaymentSerializer


# Initialize Stripe API key from Django settings
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for read-only access to Payment records.

    Permissions:
    - Staff users can view all payments.
    - Regular users can view only their own payments related to borrowings.
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Staff users can access all payments
            return Payment.objects.all()
        # Regular users see only payments linked to their borrowings
        return self.queryset.filter(borrowing__user=user)


@csrf_exempt  # Disable CSRF for webhook (Stripe signs requests)
@api_view(["POST"])
@permission_classes([AllowAny])  # Stripe webhook must be accessible publicly
def stripe_webhook(request):
    """
    Endpoint to handle Stripe webhook events.

    Handles events:
    - checkout.session.completed: marks payment as PAID and updates borrowing status.
    - checkout.session.expired, payment_intent.canceled: cancels payment and restores book inventory.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(f"Stripe webhook verification failed: {e}")
        return Response(status=status.HTTP_400_BAD_REQUEST)

    event_type = event["type"]
    session = event["data"]["object"]

    try:
        payment = Payment.objects.get(session_id=session["id"])
    except Payment.DoesNotExist:
        logger.error(f"Payment with session_id={session['id']} not found.")
        return Response(status=status.HTTP_404_NOT_FOUND)

    borrowing = payment.borrowing
    book = borrowing.book

    if event_type == "checkout.session.completed":
        # Mark payment as successful
        payment.status = Payment.StatusType.PAID
        payment.save()

        if payment.type == Payment.TypeType.PAYMENT:
            # Mark borrowing as active (borrowed)
            borrowing.status = Borrowing.BorrowingStatus.BORROWED
            borrowing.borrow_date = timezone.now().date()
            borrowing.save()
        elif payment.type == Payment.TypeType.FINE:
            # Fine payment processed - already marked PAID above
            logger.info(
                f"Fine payment completed and marked as PAID for borrowing id={borrowing.id}"
            )

        logger.info(f"Payment completed for session {session['id']}.")

        # Asynchronously notify via Telegram
        send_telegram_payment_notification.delay(
            {
                "user": payment.user.email,
                "type": payment.type.upper(),
                "amount": str(payment.amount),
                "borrowing_id": borrowing.id,
                "book": book.title,
            }
        )

    elif event_type in ["checkout.session.expired", "payment_intent.canceled"]:
        # If payment not completed, restore inventory and cancel borrowing/payment
        if payment.status != Payment.StatusType.PAID:
            if book.inventory is not None:
                book.inventory += 1
                book.save()
                logger.info(
                    f"Inventory restored for book id={book.id} due to {event_type} event."
                )
            else:
                logger.error(
                    f"Book inventory is None for book id={book.id} on {event_type} event."
                )

            payment.status = Payment.StatusType.CANCELED
            payment.save()

            borrowing.status = Borrowing.BorrowingStatus.CANCELED
            borrowing.save()

    else:
        # Unhandled events are logged for later analysis
        logger.debug(f"Unhandled Stripe event type: {event_type}")

    return Response(status=status.HTTP_200_OK)
