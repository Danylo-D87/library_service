from django.urls import path
from .views import StripeWebhookAPIView, CreatePaymentSessionAPIView

app_name = "payments"

urlpatterns = [
    path("payments/create-session/<int:borrowing_id>/", CreatePaymentSessionAPIView.as_view(), name="create-payment-session"),
    path("payments/webhook/", StripeWebhookAPIView.as_view(), name="stripe-webhook"),
]
