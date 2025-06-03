import stripe
from django.conf import settings
from django.utils import timezone

from .models import Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_borrowing_fee(borrowing):
    daily_fee = borrowing.book.daily_fee

    start_date = borrowing.borrow_date or timezone.now().date()
    days = (borrowing.expected_return_date - start_date).days

    if days <= 0:
        raise ValueError("Expected return date must be after start date")

    return daily_fee * days


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
