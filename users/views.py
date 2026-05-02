from django.contrib.auth import login, logout, update_session_auth_hash
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DIETARY_CHOICES
from .serializers import LoginSerializer, ProfileSerializer, RegisterSerializer


class RegisterPageView(TemplateView):
    """GET /register/ — Registration Form HTML page."""
    template_name = "users/register.html"


class LoginPageView(TemplateView):
    """
    GET /login/
    Login form HTML page.
    """
    template_name = "users/login.html"


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new user account.
    Request:
        email     — unique, case-insensitive email address
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


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticates the user and establishes their session.
    Returns 200 with id and email on success.
    Returns a generic error on failure to prevent user enumeration.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response({"id": user.pk, "email": user.email}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Logout the active session.
    Returns 204 No Content.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfilePageView(TemplateView):
    """
    GET /profile/
    Profile settings HTML page.
    """
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dietary_choices"] = DIETARY_CHOICES
        return ctx


class ProfileView(APIView):
    """
    GET  /api/auth/profile/ — Return current user's profile.
    PATCH /api/auth/profile/ — Update user's profile data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile
        return Response({
            "email": user.email,
            "dietary_preferences": profile.dietary_preferences,
        })

    def patch(self, request):
        user = request.user
        serializer = ProfileSerializer(
            user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if serializer.validated_data.get("new_password"):
            update_session_auth_hash(request, user)
        return Response({"email": user.email}, status=status.HTTP_200_OK)

