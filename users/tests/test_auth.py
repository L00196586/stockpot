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
        self.assertEqual(response.data["email"], self.valid_payload["email"])

    def test_login_does_not_return_password(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertNotIn("password", response.data)

    def test_login_is_case_insensitive_for_email(self):
        payload = self.valid_payload
        payload["email"] = "TEST@EXAMPLE.COM"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_is_established_after_login(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Authenticated session should allow access to a protected endpoint
        stock_url = reverse("stock-list-create")
        response2 = self.client.get(stock_url)
        self.assertNotEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

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


class LogoutViewTests(TestCase):
    """Tests for POST /api/auth/logout/"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("auth-login")
        self.logout_url = reverse("auth-logout")
        self.user = User.objects.create_user(
            username="logout@example.com",
            email="logout@example.com",
            password="SecurePass123!",
        )
        self.login_payload = {
            "email": "logout@example.com",
            "password": "SecurePass123!",
        }

    # TODO: If there's time, this implementation (reusable function with POST request) could be implemented in other tests as well to reduce code duplication.
    def _login(self):
        return self.client.post(self.login_url, self.login_payload, format="json")

    # Success case

    def test_logout_returns_204(self):
        self._login()
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logout_destroys_session(self):
        self._login()
        self.client.post(self.logout_url)
        # After logout the protected endpoint should reject the request
        stock_url = reverse("stock-list-create")
        response = self.client.get(stock_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Unauthenticated

    def test_unauthenticated_logout_returns_403(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UnauthenticatedAccessTests(TestCase):
    """Verify protected endpoints reject unauthenticated requests."""

    def setUp(self):
        self.client = APIClient()

    def test_stock_list_requires_auth(self):
        response = self.client.get(reverse("stock-list-create"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ingredient_list_requires_auth(self):
        response = self.client.get(reverse("ingredient-list-create"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
