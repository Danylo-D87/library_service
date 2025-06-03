from django.db import models


class Payment(models.Model):

    class StatusType(models.TextChoices):
        PENDING  = "PENDING", "Pending"
        PAID  = "PAID", "Paid"

    class TypeType(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        FINE  = "FINE", "Fine"

    status = models.CharField(
        max_length=10,
        choices=StatusType.choices,
        default=StatusType.PENDING,
    )
    type = models.CharField(
        max_length=10,
        choices=TypeType.choices,
        default=TypeType.PAYMENT,
    )
    borrowing = models.ForeignKey(
        "borrowings.Borrowing",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    session_url = models.URLField(blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Payment({self.id}) - Status: {self.status} | Type: {self.type}"
