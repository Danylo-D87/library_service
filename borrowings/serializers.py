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
        )
        read_only_fields = ("borrow_date", "user")

    def validate(self, data):
        expected_return_date = data.get("expected_return_date")
        borrow_date = timezone.now().date()

        if expected_return_date < borrow_date:
            raise serializers.ValidationError("Expected return date cannot be before borrow date")

        return data

    def create(self, validated_data):
        book = validated_data["book"]

        if book.inventory <= 0:
            raise serializers.ValidationError("Book inventory is empty")

        # Вилучаємо user з context, а не з validated_data
        user = self.context["request"].user

        book.inventory -= 1
        book.save()

        borrowing = Borrowing.objects.create(
            book=book,
            expected_return_date=validated_data["expected_return_date"],
            user=user
        )

        return borrowing

    def update(self, instance, validated_data):
        actual_return_date = validated_data.get("actual_return_date")

        if actual_return_date is not None and instance.actual_return_date is None:
            instance.actual_return_date = actual_return_date
            book = instance.book
            book.inventory += 1
            book.save()

        instance.save()
        return instance
