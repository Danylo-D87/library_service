from django.utils.dateparse import parse_datetime
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.permissions import IsStaffUser
from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer


class BorrowingsViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer

    def get_permissions(self):
        if self.request.user.is_staff:
            return [IsStaffUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        is_active = self.request.query_params.get("is_active", None)
        if is_active:
            if is_active.lower() in ["true", "1"]:
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() in ["false", "0"]:
                queryset = queryset.filter(actual_return_date__isnull=False)

        user_id = self.request.query_params.get("user_id", None)
        if user_id and user.is_staff:
            queryset = queryset.filter(user_id=user_id)

        return queryset


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        borrowing = serializer.save()

        return Response(self.get_serializer(borrowing).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response({"error": "Book has already been returned"}, status=status.HTTP_400_BAD_REQUEST)

        actual_return_date_str = request.data.get('actual_return_date')
        if not actual_return_date_str:
            return Response({"detail": "actual_return_date is required."}, status=status.HTTP_400_BAD_REQUEST)

        actual_return_date = parse_datetime(actual_return_date_str)
        if not actual_return_date:
            return Response({"detail": "actual_return_date format is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        if actual_return_date > borrowing.expected_return_date:
            return Response({"detail": "actual_return_date is late"}, status=status.HTTP_400_BAD_REQUEST)

        borrowing.actual_return_date = actual_return_date
        borrowing.save()

        book = borrowing.book
        book.inventory += 1
        book.save()

        return Response(self.get_serializer(borrowing).data)