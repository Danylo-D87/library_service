from django.db import models

class Payment(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
    )
    TYPE_CHOICES = (
        ("PAYMENT", "Payment"),
        ("FINE", "Fine"),
    )

    borrowing = models.ForeignKey("borrowings.Borrowing", on_delete=models.CASCADE, related_name="payments")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    session_url = models.URLField(blank=True, null=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status} - {self.type}"
