from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import stripe
from django.conf import settings

from borrowings.models import Borrowing
from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY

class CreatePaymentSessionAPIView(APIView):
    def post(self, request, borrowing_id):
        borrowing = get_object_or_404(Borrowing, id=borrowing_id)

        # Перевірка оплати
        if borrowing.payments.filter(status="PAID").exists():
            return Response({"detail": "Borrow already paid"}, status=status.HTTP_400_BAD_REQUEST)

        # Тут має бути логіка розрахунку суми — можна тимчасово заглушити:
        money_to_pay = 100  # example static value, заміни на свою логіку

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Borrow payment for book {borrowing.book_id}",
                        },
                        "unit_amount": int(money_to_pay * 100),  # в центах
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="https://yourfrontend.com/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://yourfrontend.com/payment-cancel",
            )

            payment = Payment.objects.create(
                borrowing=borrowing,
                status="PENDING",
                type="PAYMENT",
                session_id=session.id,
                session_url=session.url,
                money_to_pay=money_to_pay,
            )

            return Response({"session_url": session.url}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StripeWebhookAPIView(APIView):
    # Вимикаємо CSRF, бо Stripe буде зовнішнім клієнтом
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.headers.get("Stripe-Signature")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Обробка події успішної оплати
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session.get("id")

            try:
                payment = Payment.objects.get(session_id=session_id)
                payment.status = "PAID"
                payment.save()
            except Payment.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_200_OK)
