from rest_framework.routers import DefaultRouter

from borrowings.views import BorrowingViewSet

app_name = "borrowing"

router = DefaultRouter()
router.register("borrowings", BorrowingViewSet, basename="borrowings")

urlpatterns = [
    *router.urls,
]
