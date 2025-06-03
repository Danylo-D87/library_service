import stripe
from django.conf import settings
from .models import Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_payment_session(borrowing, payment_type, amount_usd):
    amount_cents = int(amount_usd * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Library {payment_type} for book '{borrowing.book.title}'",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={
            "borrowing_id": borrowing.id,
            "payment_type": payment_type,
        },
    )

    return Payment.objects.create(
        borrowing=borrowing,
        type=payment_type,
        money_to_pay=amount_usd,
        session_url=session.url,
        session_id=session.id,
        status=Payment.StatusType.PENDING
    )
