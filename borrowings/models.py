from django.db import models

from config import settings


class Borrowing(models.Model):
    book_id = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="borrowings")
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Borrowing: {self.book_id} by {self.user_id}"

