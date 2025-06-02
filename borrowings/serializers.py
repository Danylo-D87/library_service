from django.db import transaction
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
        read_only_fields = ("borrow_date", "user", "status")

    def validate(self, data):
        expected_return_date = data.get("expected_return_date")
        borrow_date = timezone.now().date()

        if expected_return_date < borrow_date:
            raise serializers.ValidationError("Expected return date cannot be before borrow date")

        return data

    def create(self, validated_data):
        user = self.context["request"].user

        has_unpaid = Borrowing.objects.filter(user=user).exclude(payments__status="PAID").exists()
        if has_unpaid:
            raise serializers.ValidationError("You have unpaid borrowings. Please complete payment before creating new one.")

        book = validated_data["book"]
        if book.inventory <= 0:
            raise serializers.ValidationError("Book inventory is empty")

        with transaction.atomic():
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
        if actual_return_date and not instance.actual_return_date:
            instance.actual_return_date = actual_return_date
            instance.book.inventory += 1
            instance.book.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance