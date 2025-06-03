from django.urls import path
from rest_framework.routers import DefaultRouter

from borrowings.views import BorrowingViewSet, BorrowingCreateViewSet

app_name = "borrowing"

router = DefaultRouter()
router.register(r"", BorrowingViewSet, basename="borrowings")

urlpatterns = router.urls
