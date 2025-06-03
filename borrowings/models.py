from django.db import models

from config import settings


class Borrowing(models.Model):

    class BorrowingStatus(models.TextChoices):
        BORROWED = "BORROWED", "Borrowed"
        RETURNED = "RETURNED", "Returned"
        WAITING_PAYMENT = "WAITING_PAYMENT", "Waiting Payment"
        CANCELED = "CANCELED", "Canceled"

    book = models.ForeignKey(
        "books.Book", on_delete=models.CASCADE, related_name="borrowings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings"
    )
    borrow_date = models.DateField(null=True, blank=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=BorrowingStatus.choices,
        default=BorrowingStatus.WAITING_PAYMENT,
    )

    def __str__(self):
        return f"Borrowing: {self.book.title} by {self.user.email}"
