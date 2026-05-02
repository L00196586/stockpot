from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def make_user(email="user@example.com", password="Password1!"):
    return User.objects.create_user(username=email, email=email, password=password)


class ProfileGetTests(TestCase):
    """Tests for GET /api/auth/profile/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-profile")
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def test_get_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_returns_email(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["email"], self.user.email)

    def test_get_returns_dietary_preferences(self):
        self.user.profile.dietary_preferences = ["vegan"]
        self.user.profile.save()
        response = self.client.get(self.url)
        self.assertIn("dietary_preferences", response.data)
        self.assertEqual(response.data["dietary_preferences"], ["vegan"])

    def test_get_returns_empty_dietary_preferences_by_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["dietary_preferences"], [])


class ProfilePatchEmailTests(TestCase):
    """Tests for PATCH /api/auth/profile/ Updating email"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-profile")
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def _patch(self, data):
        return self.client.patch(self.url, data, format="json")

    def test_patch_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self._patch({"email": "new@example.com"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_email_returns_200(self):
        response = self._patch({"email": "new@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_email_updates_email(self):
        self._patch({"email": "updated@example.com"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")

    def test_patch_email_case_insensitive_normalised(self):
        self._patch({"email": "UPPER@EXAMPLE.COM"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "upper@example.com")

    def test_patch_email_rejects_duplicate(self):
        make_user(email="taken@example.com")
        response = self._patch({"email": "taken@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_same_email_is_allowed(self):
        response = self._patch({"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfilePatchDietaryTests(TestCase):
    """Tests for PATCH /api/auth/profile/ Updating dietary preferences"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-profile")
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def _patch(self, data):
        return self.client.patch(self.url, data, format="json")

    def test_patch_dietary_returns_200(self):
        response = self._patch({"dietary_preferences": ["vegan"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_dietary_saves_preferences(self):
        self._patch({"dietary_preferences": ["vegan", "gluten_free"]})
        self.user.profile.refresh_from_db()
        self.assertCountEqual(self.user.profile.dietary_preferences, ["vegan", "gluten_free"])

    def test_patch_dietary_rejects_invalid_key(self):
        response = self._patch({"dietary_preferences": ["not_a_diet"]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_dietary_dont_duplicate(self):
        self._patch({"dietary_preferences": ["vegan", "vegan"]})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.dietary_preferences.count("vegan"), 1)

    def test_patch_dietary_can_clear_preferences(self):
        self.user.profile.dietary_preferences = ["vegan"]
        self.user.profile.save()
        self._patch({"dietary_preferences": []})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.dietary_preferences, [])


class ProfilePatchPasswordTests(TestCase):
    """Tests for PATCH /api/auth/profile/ Updating password"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-profile")
        self.user = make_user(password="OldPassword1!")
        self.client.force_authenticate(user=self.user)

    def _patch(self, data):
        return self.client.patch(self.url, data, format="json")

    def test_patch_without_password_fields_returns_200(self):
        response = self._patch({"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_with_matching_new_password_returns_200(self):
        response = self._patch({"new_password": "NewPassword2@", "new_password2": "NewPassword2@"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_with_new_password_actually_changes_password(self):
        self._patch({"new_password": "NewPassword2@", "new_password2": "NewPassword2@"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword2@"))

    def test_patch_with_mismatched_passwords_returns_400(self):
        response = self._patch({"new_password": "NewPassword2@", "new_password2": "Different3#"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_with_weak_password_returns_400(self):
        response = self._patch({"new_password": "abc", "new_password2": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_with_blank_password_fields_does_not_change_password(self):
        self._patch({"new_password": "", "new_password2": ""})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword1!"))

    def test_patch_can_update_email_and_password_together(self):
        response = self._patch({
            "email": "changed@example.com",
            "new_password": "NewPassword2@",
            "new_password2": "NewPassword2@",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "changed@example.com")
        self.assertTrue(self.user.check_password("NewPassword2@"))

    def test_profile_still_accessible_after_password_change(self):
        self._patch({"new_password": "NewPassword2@", "new_password2": "NewPassword2@"})
        profile_res = self.client.get(self.url)
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)

