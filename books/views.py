from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, AllowAny

from books.models import Book
from config.permissions import IsStaffUser
from books.serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_permissions(self):
        if self.action in SAFE_METHODS:
            return [AllowAny()]
        return [IsStaffUser()]
