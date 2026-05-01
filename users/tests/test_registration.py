from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RegistrationViewTest(APITestCase):
    """Tests for POST /api/auth/register/"""

    def setUp(self):
        self.url = reverse("auth-register")
        self.valid_payload = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
        }

    # Success case

    def test_successful_registration_returns_201(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_successful_registration_creates_user_in_database(self):
        self.client.post(self.url, self.valid_payload, format="json")
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_successful_registration_response_contains_id_and_email(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertIn("id", response.data)
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"], "newuser@example.com")

    def test_password_is_not_returned_in_response(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertNotIn("password", response.data)
        self.assertNotIn("password2", response.data)

    def test_password_is_hashed_in_database(self):
        self.client.post(self.url, self.valid_payload, format="json")
        user = User.objects.get(email="newuser@example.com")
        self.assertNotEqual(user.password, self.valid_payload["password"])

    def test_user_check_password_with_registered_credentials(self):
        self.client.post(self.url, self.valid_payload, format="json")
        user = User.objects.get(email="newuser@example.com")
        self.assertTrue(user.check_password(self.valid_payload["password"]))

    def test_email_is_stored_lowercased(self):
        payload = self.valid_payload
        payload["email"] = "UPPER@Example.COM"
        self.client.post(self.url, payload, format="json")
        user = User.objects.get(email="upper@example.com")
        self.assertEqual(user.email, "upper@example.com")

    def test_username_is_set_to_email(self):
        self.client.post(self.url, self.valid_payload, format="json")
        user = User.objects.get(email="newuser@example.com")
        self.assertEqual(user.username, "newuser@example.com")

    # Endpoint is public

    def test_registration_does_not_require_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Duplicate email

    def test_duplicate_email_returns_400(self):
        self.client.post(self.url, self.valid_payload, format="json")
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_is_case_insensitive(self):
        self.client.post(self.url, self.valid_payload, format="json")
        payload = self.valid_payload
        payload["email"] = "NEWUSER@EXAMPLE.COM"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_error_is_on_email_field(self):
        self.client.post(self.url, self.valid_payload, format="json")
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertIn("email", response.data)

    # Password confirmation different

    def test_password_different_returns_400(self):
        payload = self.valid_payload
        payload["password2"] = "DifferentPass999!"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_different_error_is_on_password2_field(self):
        payload = self.valid_payload
        payload["password2"] = "DifferentPass999!"
        response = self.client.post(self.url, payload, format="json")
        self.assertIn("password2", response.data)

    def test_password_different_does_not_create_user(self):
        payload = self.valid_payload
        payload["password2"] = "DifferentPass999!"
        self.client.post(self.url, payload, format="json")
        self.assertFalse(User.objects.filter(email=self.valid_payload["email"]).exists())

    # Invalid password

    def test_too_short_password_returns_400(self):
        payload = self.valid_payload
        payload["password"] = "Ab1!"
        payload["password2"] = "Ab1!"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_entirely_numeric_password_returns_400(self):
        payload = self.valid_payload
        payload["password"] = "12345678"
        payload["password2"] = "12345678"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_common_password_returns_400(self):
        payload = self.valid_payload
        payload["password"] = "password123"
        payload["password2"] = "password123"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Missing fields

    def test_missing_email_returns_400(self):
        payload = {"password": "SecurePass123!", "password2": "SecurePass123!"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_missing_password_returns_400(self):
        payload = {"email": "user@example.com", "password2": "SecurePass123!"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_missing_password2_returns_400(self):
        payload = {"email": "user@example.com", "password": "SecurePass123!"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", response.data)

    def test_empty_payload_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Invalid email format

    def test_invalid_email_format_returns_400(self):
        payload = {**self.valid_payload, "email": "not-an-email"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    # GET is not allowed

    def test_get_method_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
