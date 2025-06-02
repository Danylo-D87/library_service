from django.db import models, transaction
from config import settings
from django.utils import timezone


class Borrowing(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("RETURNED", "Returned"),
        ("OVERDUE", "Overdue"),
    )

    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    def update_status(self):
        if self.actual_return_date:
            self.status = "RETURNED"
        elif timezone.now().date() > self.expected_return_date:
            self.status = "OVERDUE"
        else:
            self.status = "ACTIVE"

    def save(self, *args, **kwargs):
        self.update_status()
        super().save(*args, **kwargs)

    @property
    def is_paid(self):
        return self.payments.filter(status="PAID").exists()

    def __str__(self):
        return f"Borrowing: {self.book.title} by {self.user.email}"