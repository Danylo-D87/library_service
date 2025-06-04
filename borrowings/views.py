import logging
from decimal import Decimal

from django.utils import timezone
from rest_framework import status, mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import GenericViewSet

from config.permissions import IsStaffUser
from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer
from payments.services import (
    create_stripe_payment_session,
    calculate_borrowing_fee,
    calculate_fine,
)

logger = logging.getLogger(__name__)


class BorrowingViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage borrowings of books.

    Permissions:
    - Staff users have full access.
    - Regular authenticated users can only view and manage their own borrowings.

    Filtering:
    - `is_active` query param: filter active borrowings (not returned) or inactive (returned).
    - `user_id` filter is restricted to staff users only.

    Create:
    - Checks book inventory before allowing borrowing.
    - Decreases inventory upon borrowing creation.
    - Calculates fee and creates Stripe payment session.

    Custom action `return_book`:
    - Marks borrowing as returned.
    - Increments book inventory.
    - Calculates fines (if any) and creates Stripe payment session for fines.
    """

    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer

    def get_permissions(self):
        if self.request.user.is_staff:
            return [IsStaffUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = Borrowing.objects.all()

        if not user.is_staff:
            # Non-staff users see only their borrowings
            queryset = queryset.filter(user=user)

        # Filter by active/inactive borrowings if requested
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ["true", "1"]:
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() in ["false", "0"]:
                queryset = queryset.filter(actual_return_date__isnull=False)

        # Staff-only filter by user_id
        user_id = self.request.query_params.get("user_id")
        if user_id:
            if not user.is_staff:
                raise ValidationError("Only staff users can filter by user_id.")
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override create to:
        - Validate data.
        - Check book inventory.
        - Create borrowing with status WAITING_PAYMENT.
        - Decrease book inventory.
        - Calculate fee and create Stripe checkout session.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        book = serializer.validated_data["book"]

        if book.inventory <= 0:
            raise ValidationError("Book inventory is empty")

        borrowing = Borrowing.objects.create(
            book=book,
            expected_return_date=serializer.validated_data["expected_return_date"],
            user=user,
            status=Borrowing.BorrowingStatus.WAITING_PAYMENT,
        )

        # Update inventory
        book.inventory -= 1
        book.save()

        try:
            amount = calculate_borrowing_fee(borrowing)
        except ValueError as e:
            # Rollback borrowing creation if fee calculation fails
            borrowing.delete()
            raise ValidationError(str(e))

        payment = create_stripe_payment_session(
            borrowing, payment_type="PAYMENT", amount_usd=amount
        )

        borrowing_data = self.get_serializer(borrowing).data
        return Response(
            {
                "checkout_url": payment.session_url,
                "borrowing": borrowing_data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        """
        Custom action to return a borrowed book:
        - Checks if book is already returned.
        - Updates actual return date and status.
        - Increments book inventory.
        - Calculates fine, if applicable, and creates Stripe fine payment session.
        """
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            raise ValidationError("Book has already been returned.")

        actual_return_date = timezone.now().date()
        borrowing.actual_return_date = actual_return_date
        borrowing.status = Borrowing.BorrowingStatus.RETURNED
        borrowing.save()

        # Restore book inventory
        book = borrowing.book
        book.inventory += 1
        book.save()

        fine_amount = Decimal("0.00")
        try:
            fine_amount = calculate_fine(borrowing)
        except Exception as e:
            logger.error(
                f"Fine calculation failed for borrowing id={borrowing.id}: {e}"
            )

        if fine_amount > Decimal("0.00"):
            fine_payment = create_stripe_payment_session(
                borrowing, payment_type="FINE", amount_usd=fine_amount
            )
            return Response(
                {
                    "borrowing": self.get_serializer(borrowing).data,
                    "fine_payment_url": fine_payment.session_url,
                    "fine_amount": fine_amount,
                }
            )

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data)


class BorrowingCreateViewSet(mixins.CreateModelMixin, GenericViewSet):
    """
    Dedicated ViewSet for creating Borrowings only.

    Permissions:
    - Only authenticated users can create borrowings.
    """

    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated()]
