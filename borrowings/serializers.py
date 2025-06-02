from django.utils import timezone
from rest_framework import serializers

from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "book_id",
            "user_id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
        )

    def validate(self, data):
        expected_return_date = data.get("expected_return_date")
        borrow_date = data.get("borrow_date")

        if expected_return_date < borrow_date:
            raise serializers.ValidationError("Expected return date cannot be before borrow date")

        return data

    def create(self, validated_data):
        book = validated_data.pop("book")

        if book.inventory <= 0:
            raise serializers.ValidationError("Book inventory is empty")

        book.inventory -= 1
        book.save()

        borrowing = Borrowing.objects.create(
            **validated_data
        )

        return borrowing

    def update(self, instance, validated_data):
        actual_return_date = validated_data.get("actual_return_date")

        if actual_return_date is not None:
            instance.actual_return_date = actual_return_date
            book = instance.book
            book.inventory += 1
            book.save()

        instance.save()
        return instance
