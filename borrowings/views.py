from django.utils.dateparse import parse_date
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from config.permissions import IsStaffUser
from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer


class BorrowingViewSet(viewsets.ModelViewSet):
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
            queryset = queryset.filter(user=user)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ["true", "1"]:
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() in ["false", "0"]:
                queryset = queryset.filter(actual_return_date__isnull=False)

        user_id = self.request.query_params.get("user_id")
        if user_id:
            if not user.is_staff:
                raise ValidationError("Only staff users can filter by user_id.")
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            raise ValidationError("Book has already been returned.")

        actual_return_date_str = request.data.get("actual_return_date")
        if not actual_return_date_str:
            raise ValidationError("actual_return_date is required.")

        actual_return_date = parse_date(actual_return_date_str)
        if not actual_return_date:
            raise ValidationError("actual_return_date format is invalid.")

        borrowing.actual_return_date = actual_return_date
        borrowing.save()

        book = borrowing.book
        book.inventory += 1
        book.save()

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data)
