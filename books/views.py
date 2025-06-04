from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter

from books.models import Book
from config.permissions import IsStaffUser
from books.serializers import BookSerializer


@extend_schema(
    summary="Retrieve, create, update, or delete books",
    description=(
        "Endpoint to manage books in the library.\n\n"
        "- Safe methods (GET, HEAD, OPTIONS) are accessible to anyone.\n"
        "- Unsafe methods (POST, PUT, PATCH, DELETE) require staff user permissions."
    ),
    parameters=[
        OpenApiParameter(
            name="id",
            description="Unique identifier of the book (used for retrieve, update, delete).",
            required=False,
            type=int,
        ),
        OpenApiParameter(
            name="search",
            description="Search books by title or author (query parameter).",
            required=False,
            type=str,
        ),
    ],
    responses={
        200: BookSerializer(many=True),
        201: BookSerializer,
        400: "Bad Request",
        403: "Forbidden",
        404: "Not Found",
    },
)
class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling Books.

    Permissions:
    - SAFE_METHODS: AllowAny (read-only access for everyone)
    - Other methods: IsStaffUser (restricted to staff)
    """

    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_permissions(self):
        if self.action in SAFE_METHODS:
            return [AllowAny()]
        return [IsStaffUser()]
