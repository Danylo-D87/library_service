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
from .models import Payment
from .serializers import PaymentSerializer


stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return self.queryset.filter(borrowing__user=self.request.user)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
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
        payment.status = Payment.StatusType.PAID
        payment.save()

        if payment.type == Payment.TypeType.PAYMENT:
            borrowing.status = Borrowing.BorrowingStatus.BORROWED
            borrowing.borrow_date = timezone.now().date()
            borrowing.save()

        elif payment.type == Payment.TypeType.FINE:
            payment.status = Payment.StatusType.PAID
            payment.save()
            logger.info(f"Fine payment completed and marked as PAID for borrowing id={borrowing.id}")

        logger.info(f"Payment completed for session {session['id']}.")

    elif event_type in ["checkout.session.expired", "payment_intent.canceled"]:
        if payment.status != Payment.StatusType.PAID:
            if book.inventory is not None:
                book.inventory += 1
                book.save()
                logger.info(f"Inventory restored for book id={book.id} due to {event_type} event.")
            else:
                logger.error(f"Book inventory is None for book id={book.id} on {event_type} event.")

            payment.status = Payment.StatusType.CANCELED
            payment.save()

            borrowing.status = Borrowing.BorrowingStatus.CANCELED
            borrowing.save()

    else:
        logger.debug(f"Unhandled Stripe event type: {event_type}")

    return Response(status=status.HTTP_200_OK)
