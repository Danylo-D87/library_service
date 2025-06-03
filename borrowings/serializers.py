from django.utils import timezone
from rest_framework import serializers

from books.models import Book
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "book",
            "user",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "status",
        )
        read_only_fields = ("id", "borrow_date", "user", "status", "actual_return_date")

    def validate(self, data):
        expected_return_date = data.get("expected_return_date")
        borrow_date = timezone.now().date()

        if expected_return_date < borrow_date:
            raise serializers.ValidationError(
                "Expected return date cannot be before borrow date"
            )

        book = data.get("book")
        if book.inventory <= 0:
            raise serializers.ValidationError("Book inventory is empty")

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        borrowing = Borrowing.objects.create(
            book=validated_data["book"],
            expected_return_date=validated_data["expected_return_date"],
            user=user,
            status=Borrowing.BorrowingStatus.WAITING_PAYMENT,
            borrow_date=None,
        )
        return borrowing

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
