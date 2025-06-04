from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from users.serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    """
    API view to register a new user.

    Uses the UserSerializer for validation and creation.
    Allows anyone to create a user (no authentication required).
    """

    serializer_class = UserSerializer


class ManageUserView(generics.RetrieveUpdateAPIView):
    """
    API view to retrieve and update the authenticated user's profile.

    Requires JWT authentication and the user to be logged in.
    The user can only access and modify their own data.
    """

    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """
        Return the current authenticated user instance.

        Ensures users can only manage their own profile.
        """
        return self.request.user
