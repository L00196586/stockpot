import datetime
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from pantry.models import Ingredient, StockItem
from pantry.services import SpoonacularError


class IngredientListCreateViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="pass")
        self.client.force_authenticate(user=self.user)
        self.flour = Ingredient.objects.create(name="Flour", unit="g")
        self.milk = Ingredient.objects.create(name="Milk", unit="L")
        self.url = reverse("ingredient-list-create")

    # Authentication

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"name": "Butter", "unit": "g"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # List

    def test_list_returns_all_ingredients(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_list_results_are_alphabetically_ordered(self):
        response = self.client.get(self.url)
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, ["Flour", "Milk"])

    def test_search_filter_returns_matching_ingredient(self):
        response = self.client.get(self.url, {"search": "Flour"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Flour")

    def test_search_filter_is_case_insensitive(self):
        response = self.client.get(self.url, {"search": "flour"})
        self.assertEqual(response.data["count"], 1)

    def test_search_filter_returns_empty_for_no_match(self):
        response = self.client.get(self.url, {"search": "zzzz"})
        self.assertEqual(response.data["count"], 0)

    # Create

    def test_create_ingredient_returns_201(self):
        response = self.client.post(self.url, {"name": "Eggs", "unit": "pcs"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_ingredient_persists_to_database(self):
        self.client.post(self.url, {"name": "Eggs", "unit": "pcs"}, format="json")
        self.assertTrue(Ingredient.objects.filter(name="Eggs").exists())

    def test_create_ingredient_response_contains_id_name_unit(self):
        response = self.client.post(self.url, {"name": "Eggs", "unit": "pcs"}, format="json")
        self.assertEqual(set(response.data.keys()), {"id", "name", "unit"})
        self.assertEqual(response.data["name"], "Eggs")
        self.assertEqual(response.data["unit"], "pcs")

    def test_create_ingredient_defaults_unit_to_grams(self):
        response = self.client.post(self.url, {"name": "Salt"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit"], "g")

    def test_create_ingredient_rejects_invalid_unit(self):
        response = self.client.post(
            self.url, {"name": "Mystery", "unit": "xyz"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unit", response.data)

    def test_create_ingredient_rejects_duplicate_name(self):
        response = self.client.post(self.url, {"name": "Flour", "unit": "kg"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_ingredient_rejects_missing_name(self):
        response = self.client.post(self.url, {"unit": "g"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StockItemListCreateViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="pass")
        self.other_user = User.objects.create_user(username="user2", password="pass")
        self.client.force_authenticate(user=self.user)
        self.flour = Ingredient.objects.create(name="Flour", unit="g")
        self.milk = Ingredient.objects.create(name="Milk", unit="L")
        self.url = reverse("stock-list-create")

    # Authentication

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url, {"ingredient_id": self.flour.pk, "quantity": "100.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # List

    def test_list_returns_only_the_authenticated_users_items(self):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        StockItem.objects.create(user=self.other_user, ingredient=self.milk, quantity=2)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["ingredient"]["name"], "Flour")

    def test_list_returns_empty_for_user_with_no_stock(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_list_response_nests_full_ingredient_data(self):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        response = self.client.get(self.url)
        item = response.data["results"][0]
        self.assertIn("ingredient", item)
        self.assertEqual(item["ingredient"]["name"], "Flour")
        self.assertEqual(item["ingredient"]["unit"], "g")

    # Create

    def test_create_stock_item_returns_201(self):
        response = self.client.post(
            self.url,
            {"ingredient_id": self.flour.pk, "quantity": "500.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_stock_item_is_scoped_to_requesting_user(self):
        self.client.post(
            self.url,
            {"ingredient_id": self.flour.pk, "quantity": "500.00"},
            format="json",
        )
        stock = StockItem.objects.get(ingredient=self.flour)
        self.assertEqual(stock.user, self.user)

    def test_create_stock_item_response_has_nested_ingredient(self):
        response = self.client.post(
            self.url,
            {"ingredient_id": self.flour.pk, "quantity": "500.00"},
            format="json",
        )
        self.assertIn("ingredient", response.data)
        self.assertEqual(response.data["ingredient"]["name"], "Flour")
        self.assertEqual(response.data["ingredient"]["unit"], "g")

    def test_create_stock_item_with_expiry_date(self):
        response = self.client.post(
            self.url,
            {
                "ingredient_id": self.flour.pk,
                "quantity": "500.00",
                "expiry_date": "2027-06-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["expiry_date"], "2027-06-01")

    def test_create_duplicate_ingredient_returns_400(self):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=100)
        response = self.client.post(
            self.url,
            {"ingredient_id": self.flour.pk, "quantity": "200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_ingredient_id_returns_400(self):
        response = self.client.post(
            self.url, {"ingredient_id": 9999, "quantity": "100.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_quantity_returns_400(self):
        response = self.client.post(
            self.url, {"ingredient_id": self.flour.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_two_different_users_can_stock_the_same_ingredient(self):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            self.url,
            {"ingredient_id": self.flour.pk, "quantity": "300.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class StockItemDetailViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="pass")
        self.other_user = User.objects.create_user(username="user2", password="pass")
        self.client.force_authenticate(user=self.user)
        self.flour = Ingredient.objects.create(name="Flour", unit="g")
        self.milk = Ingredient.objects.create(name="Milk", unit="L")
        self.stock = StockItem.objects.create(
            user=self.user, ingredient=self.flour, quantity=500
        )
        self.url = reverse("stock-detail", args=[self.stock.pk])

    # Authentication

    def test_retrieve_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Retrieve

    def test_retrieve_own_stock_item_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_response_includes_nested_ingredient_and_quantity(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["ingredient"]["name"], "Flour")
        self.assertEqual(float(response.data["quantity"]), 500.0)

    def test_retrieve_other_users_item_returns_404(self):
        other_stock = StockItem.objects.create(
            user=self.other_user, ingredient=self.milk, quantity=2
        )
        response = self.client.get(reverse("stock-detail", args=[other_stock.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Update (PUT)

    def test_put_updates_quantity_and_expiry_date(self):
        response = self.client.put(
            self.url,
            {
                "ingredient_id": self.flour.pk,
                "quantity": "999.00",
                "expiry_date": "2028-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 999)
        self.assertEqual(str(self.stock.expiry_date), "2028-01-01")

    def test_put_response_has_nested_ingredient(self):
        response = self.client.put(
            self.url,
            {"ingredient_id": self.flour.pk, "quantity": "200.00"},
            format="json",
        )
        self.assertIn("ingredient", response.data)
        self.assertEqual(response.data["ingredient"]["name"], "Flour")

    def test_put_other_users_item_returns_404(self):
        other_stock = StockItem.objects.create(
            user=self.other_user, ingredient=self.milk, quantity=2
        )
        response = self.client.put(
            reverse("stock-detail", args=[other_stock.pk]),
            {"ingredient_id": self.milk.pk, "quantity": "5.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Update (PATCH)

    def test_patch_updates_quantity_only(self):
        response = self.client.patch(self.url, {"quantity": "750.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 750)

    def test_patch_updates_expiry_date_only(self):
        response = self.client.patch(
            self.url, {"expiry_date": "2029-06-15"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.expiry_date), "2029-06-15")

    def test_patch_clears_expiry_date(self):
        self.stock.expiry_date = datetime.date(2026, 12, 1)
        self.stock.save()
        response = self.client.patch(self.url, {"expiry_date": None}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertIsNone(self.stock.expiry_date)

    def test_patch_other_users_item_returns_404(self):
        other_stock = StockItem.objects.create(
            user=self.other_user, ingredient=self.milk, quantity=2
        )
        response = self.client.patch(
            reverse("stock-detail", args=[other_stock.pk]),
            {"quantity": "99.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Delete

    def test_delete_removes_stock_item_and_returns_204(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StockItem.objects.filter(pk=self.stock.pk).exists())

    def test_delete_other_users_item_returns_404_and_does_not_delete(self):
        other_stock = StockItem.objects.create(
            user=self.other_user, ingredient=self.milk, quantity=2
        )
        response = self.client.delete(reverse("stock-detail", args=[other_stock.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(StockItem.objects.filter(pk=other_stock.pk).exists())

    def test_delete_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RecipeMatchViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test@email.com", password="SecurePass123!")
        self.other_user = User.objects.create_user(username="othertest@email.com", password="SecurePass234!")
        self.client.force_authenticate(user=self.user)
        self.flour = Ingredient.objects.create(name="Flour", unit="g")
        self.milk = Ingredient.objects.create(name="Milk", unit="L")
        self.url = reverse("recipe-match")
        self.expected_recipe = {
            "id": 1,
            "title": "Pancakes",
            "image": "https://example.com/pancakes.jpg",
            "used_count": 2,
            "missed_count": 1,
            "used_ingredients": ["Flour", "Milk"],
            "missed_ingredients": ["Eggs"],
        }

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_pantry_returns_200_with_detail_message(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertIn("empty", response.data["detail"].lower())

    @patch("pantry.views.find_recipes_by_ingredients")
    def test_returns_recipes_when_pantry_has_items(self, mock_service):
        mock_service.return_value = [self.expected_recipe]
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        StockItem.objects.create(user=self.user, ingredient=self.milk, quantity=1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Pancakes")

    @patch("pantry.views.find_recipes_by_ingredients")
    def test_only_sends_logged_user_ingredients_to_service(self, mock_service):
        mock_service.return_value = [self.expected_recipe]
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        StockItem.objects.create(user=self.other_user, ingredient=self.milk, quantity=1)

        self.client.get(self.url)

        sent_names = mock_service.call_args[0][0]
        self.assertEqual(sent_names, ["Flour"])

    @patch(
        "pantry.views.find_recipes_by_ingredients",
        side_effect=SpoonacularError("quota exceeded", status_code=402),
    )
    def test_quota_exceeded_returns_402(self, mock_service):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("detail", response.data)

    @patch(
        "pantry.views.find_recipes_by_ingredients",
        side_effect=SpoonacularError("service unavailable", status_code=503),
    )
    def test_other_service_errors_return_503(self, mock_service):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch(
        "pantry.views.find_recipes_by_ingredients",
        side_effect=SpoonacularError("timed out"),
    )
    def test_service_error_without_status_code_returns_503(self, mock_service):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("pantry.views.find_recipes_by_ingredients", return_value=[])
    def test_returns_empty_list_when_no_matching_recipes(self, mock_service):
        StockItem.objects.create(user=self.user, ingredient=self.flour, quantity=500)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class RecipeSuggestionsPageViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test@email.com", password="SecurePass123!")
        self.url = reverse("recipes-page")

    def test_renders_recipes_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pantry/recipes.html")


class PantryPageViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test@email.com", password="SecurePass123!")
        self.url = reverse("pantry-page")

    def test_renders_stock_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pantry/stock.html")

    def test_context_includes_unit_choices(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn("unit_choices", response.context)
        self.assertTrue(len(response.context["unit_choices"]) > 0)


class RecipeDetailViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test@email.com", password="SecurePass123!")
        self.client.force_authenticate(user=self.user)
        self.url_name = "recipe-detail"
        self.recipe_id = 42
        self.sample_details = {
            "id": 42,
            "title": "Spaghetti Bolognese",
            "image": "https://example.com/spag.jpg",
            "ready_in_minutes": 60,
            "prep_minutes": 15,
            "cook_minutes": 45,
            "nutrition": [{"name": "Calories", "amount": 550, "unit": "kcal"}],
            "instructions": [{"number": 1, "step": "Boil the pasta."}],
        }

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse(self.url_name, args=[self.recipe_id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("pantry.views.get_recipe_details")
    def test_returns_recipe_details_on_success(self, mock_service):
        mock_service.return_value = self.sample_details
        response = self.client.get(reverse(self.url_name, args=[self.recipe_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], 42)
        self.assertEqual(response.data["title"], "Spaghetti Bolognese")

    @patch("pantry.views.get_recipe_details")
    def test_calls_service_with_correct_recipe_id(self, mock_service):
        mock_service.return_value = self.sample_details
        self.client.get(reverse(self.url_name, args=[self.recipe_id]))
        mock_service.assert_called_once_with(self.recipe_id)

    @patch(
        "pantry.views.get_recipe_details",
        side_effect=SpoonacularError("not found", status_code=404),
    )
    def test_recipe_not_found_returns_404(self, mock_service):
        response = self.client.get(reverse(self.url_name, args=[99999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    @patch(
        "pantry.views.get_recipe_details",
        side_effect=SpoonacularError("quota exceeded", status_code=402),
    )
    def test_quota_exceeded_returns_429(self, mock_service):
        response = self.client.get(reverse(self.url_name, args=[self.recipe_id]))
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch(
        "pantry.views.get_recipe_details",
        side_effect=SpoonacularError("service error", status_code=500),
    )
    def test_other_service_errors_return_503(self, mock_service):
        response = self.client.get(reverse(self.url_name, args=[self.recipe_id]))
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class RecipeDetailPageViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test@email.com", password="SecurePass123!")
        self.recipe_id = 42
        self.url = reverse("recipe-detail-page", args=[self.recipe_id])

    def test_renders_recipe_detail_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pantry/recipe_detail.html")

    def test_context_contains_recipe_id(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["recipe_id"], self.recipe_id)
