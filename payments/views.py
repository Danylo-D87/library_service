from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe

from .models import Payment
from .serializers import PaymentSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


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
@permission_classes([AllowAny,])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            payment = Payment.objects.get(session_id=session["id"])
        except Payment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        payment.status = Payment.StatusType.PAID
        payment.save()

    return Response(status=status.HTTP_200_OK)
