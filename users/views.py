from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new user account
    Request:
        email     — unique, case-insensitive, email address
        password  — must satisfy Django's configured password validators
        password2 — must match password

    Returns 201 with the new user's id and email on success.
    Returns 400 with field errors on failure.
    Passwords are never included in any response.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"id": user.pk, "email": user.email},
            status=status.HTTP_201_CREATED,
        )
