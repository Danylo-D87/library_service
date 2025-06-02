from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from users.models import User
from borrowings.models import Borrowing


class BorrowingsTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(email="staff@example.com", password="pass", is_staff=True)
        self.regular_user = User.objects.create_user(email="user@example.com", password="pass", is_staff=False)
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            cover=Book.CoverType.SOFT,
            inventory=3,
            daily_fee="1.50"
        )

    def test_create_borrowing_decreases_inventory(self):
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-list")
        data = {
            "book": self.book.id,
            "expected_return_date": (timezone.now() + timezone.timedelta(days=7)).date().isoformat(),
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 2)
        self.assertEqual(response.data["user"], self.regular_user.id)

    def test_create_borrowing_fails_when_inventory_zero(self):
        self.book.inventory = 0
        self.book.save()

        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-list")
        data = {
            "book": self.book.id,
            "expected_return_date": (timezone.now() + timezone.timedelta(days=7)).date().isoformat(),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Book inventory is empty", str(response.data))

    def test_return_book_success_increases_inventory(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=7),
        )
        self.book.inventory = 2
        self.book.save()

        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-return-book", kwargs={"pk": borrowing.pk})
        actual_return_date = timezone.now().date().isoformat()
        response = self.client.post(url, {"actual_return_date": actual_return_date})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        borrowing.refresh_from_db()
        self.assertIsNotNone(borrowing.actual_return_date)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 3)  # +1

    def test_return_book_already_returned_error(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=7),
            actual_return_date=timezone.now().date()
        )
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-return-book", kwargs={"pk": borrowing.pk})
        response = self.client.post(url, {"actual_return_date": timezone.now().date().isoformat()})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Book has already been returned", str(response.data))

    def test_return_book_missing_actual_return_date_error(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=7),
        )
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-return-book", kwargs={"pk": borrowing.pk})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("actual_return_date is required", str(response.data))

    def test_return_book_invalid_format_actual_return_date(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=7),
        )
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-return-book", kwargs={"pk": borrowing.pk})
        response = self.client.post(url, {"actual_return_date": "not-a-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("actual_return_date format is invalid", str(response.data))

    def test_get_queryset_filters_is_active(self):
        active_borrow = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=5),
        )
        inactive_borrow = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() - timezone.timedelta(days=5),
            actual_return_date=timezone.now().date(),
        )
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-list")

        response = self.client.get(url, {"is_active": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        borrow_ids = [borrow["id"] for borrow in response.data]
        self.assertIn(active_borrow.id, borrow_ids)
        self.assertNotIn(inactive_borrow.id, borrow_ids)

        response = self.client.get(url, {"is_active": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        borrow_ids = [borrow["id"] for borrow in response.data]
        self.assertIn(inactive_borrow.id, borrow_ids)
        self.assertNotIn(active_borrow.id, borrow_ids)

    def test_regular_user_sees_only_own_borrowings(self):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        borrow_self = Borrowing.objects.create(
            book=self.book,
            user=self.regular_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=1),
        )
        borrow_other = Borrowing.objects.create(
            book=self.book,
            user=other_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=1),
        )
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("borrowing:borrowings-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        borrow_ids = [borrow["id"] for borrow in response.data]
        self.assertIn(borrow_self.id, borrow_ids)
        self.assertNotIn(borrow_other.id, borrow_ids)

    def test_staff_user_sees_all_borrowings(self):
        other_user = User.objects.create_user(email="other2@example.com", password="pass")
        borrow_self = Borrowing.objects.create(
            book=self.book,
            user=self.staff_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=1),
        )
        borrow_other = Borrowing.objects.create(
            book=self.book,
            user=other_user,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=1),
        )
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("borrowing:borrowings-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str(borrow_self.id), str(response.data))
        self.assertIn(str(borrow_other.id), str(response.data))
