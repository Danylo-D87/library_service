from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, stripe_webhook

app_name = "payments"

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payments")

urlpatterns = [
    path("", include(router.urls)),
    path("webhook/", stripe_webhook, name="stripe-webhook"),
]
