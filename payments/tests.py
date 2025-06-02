import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from borrowings.models import Borrowing
from books.models import Book
from payments.models import Payment
from django.urls import reverse
from unittest.mock import patch
from datetime import date, timedelta
from unittest.mock import Mock


User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="testuser@example.com",
        password="password"
    )

@pytest.fixture
def book(db):
    return Book.objects.create(title="Test Book", daily_fee=5.0, inventory=10)

@pytest.fixture
def borrowing(db, user, book):
    return Borrowing.objects.create(
        user=user,
        book=book,
        expected_return_date=date.today() + timedelta(days=7)
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
@patch("stripe.checkout.Session.create")
def test_create_payment_session_success(mock_stripe_create, api_client, book, user):

    mock_stripe_create.return_value = Mock(
        id="sess_123",
        url="https://stripe.com/checkout/session/sess_123"
    )

    url = reverse("borrowing:borrowings-list")

    data = {
        "book": book.id,
        "expected_return_date": (date.today() + timedelta(days=7)).isoformat()
    }

    response = api_client.post(url, data, format="json")
    print(response.data)  # для дебагу, можна потім прибрати

    assert response.status_code in [200, 201]

    borrowing = Borrowing.objects.get(user=user)
    payment = Payment.objects.filter(borrowing=borrowing).last()

    assert payment is not None
    assert payment.status == "PENDING"
    assert payment.session_id == "sess_123"
