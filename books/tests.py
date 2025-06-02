from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from books.permissions import IsStaffUser

User = get_user_model()

class IsStaffUserPermissionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsStaffUser()

        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='pass'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        self.normal_user = User.objects.create_user(
            email='normal@example.com',
            password='pass'
        )
        self.normal_user.is_staff = False
        self.normal_user.save()

    def test_permission_staff_user(self):
        request = self.factory.get('/fake-url/')
        request.user = self.staff_user
        self.assertTrue(self.permission.has_permission(request, None))

    def test_permission_normal_user(self):
        request = self.factory.get('/fake-url/')
        request.user = self.normal_user
        self.assertFalse(self.permission.has_permission(request, None))

    def test_permission_anonymous_user(self):
        request = self.factory.get('/fake-url/')
        request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(request, None))
