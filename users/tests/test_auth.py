from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class LoginViewTests(TestCase):
    """Tests for POST /api/auth/login/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-login")
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePass123!",
        )
        self.valid_payload = {
            "email": "test@example.com",
            "password": "SecurePass123!",
        }

    def _post(self, email, password):
        return self.client.post(self.url, self.valid_payload, format="json")

    # Success case

    def test_login_returns_200_with_valid_credentials(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_response_contains_user_id_and_email(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertIn("id", response.data)
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"], valid_payload["email"])

    def test_login_does_not_return_password(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertNotIn("password", response.data)

    def test_login_is_case_insensitive_for_email(self):
        payload = self.valid_payload
        payload["email"] = "TEST@EXAMPLE.COM"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # TODO: Authenticated session should allow access to a protected endpoint

    # Wrong credentials

    def test_wrong_password_returns_400(self):
        payload = self.valid_payload
        payload["password"] = "WrongPassword1!"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_email_returns_400(self):
        payload = self.valid_payload
        payload["email"] = "wrong_email@email.com"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_password_generic_error_message(self):
        # Both wrong email and wrong password use the same message to prevent user enumeration
        payload_pass = self.valid_payload
        payload_pass["password"] = "WrongPassword1!"
        payload_email = self.valid_payload
        payload_email["email"] = "wrong_email@email.com"
        response_wrong_pass = self.client.post(self.url, payload_pass, format="json")
        response_wrong_email = self.client.post(self.url, payload_email, format="json")
        self.assertEqual(
            response_wrong_pass.data["non_field_errors"],
            response_wrong_email.data["non_field_errors"],
        )

    def test_error_is_not_field_specific(self):
        # Error must appear under non_field_errors, not email or password
        payload = self.valid_payload
        payload["email"] = "wrong_email@email.com"
        response = self.client.post(self.url, payload, format="json")
        self.assertNotIn("email", response.data)
        self.assertNotIn("password", response.data)
        self.assertIn("non_field_errors", response.data)

    # Inactive account

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Missing fields

    def test_missing_email_returns_400(self):
        response = self.client.post(self.url, {"password": "SecurePass123!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password_returns_400(self):
        response = self.client.post(self.url, {"email": "test@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_body_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

