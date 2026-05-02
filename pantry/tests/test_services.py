from unittest.mock import patch

import requests
from django.test import TestCase, override_settings
from pantry.services import SpoonacularError, find_recipes_by_ingredients, get_recipe_details


class RecipeSuggestionsServiceTest(TestCase):

    def setUp(self):
        self.sample_api_response = [
            {
                "id": 1,
                "title": "Pancakes",
                "image": "https://example.com/pancakes.jpg",
                "usedIngredientCount": 2,
                "missedIngredientCount": 1,
                "usedIngredients": [{"name": "Flour"}, {"name": "Milk"}],
                "missedIngredients": [{"name": "Eggs"}],
            }
        ]
        self.expected_recipe = {
            "id": 1,
            "title": "Pancakes",
            "image": "https://example.com/pancakes.jpg",
            "used_count": 2,
            "missed_count": 1,
            "used_ingredients": ["Flour", "Milk"],
            "missed_ingredients": ["Eggs"],
        }

    @override_settings(SPOONACULAR_API_KEY="")
    def test_raises_when_api_key_is_not_configured(self):
        with self.assertRaises(SpoonacularError) as context:
            find_recipes_by_ingredients(["Flour"])
        self.assertIn("API key", str(context.exception))

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_returns_normalised_recipe_list_on_success(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.sample_api_response

        result = find_recipes_by_ingredients(["Flour", "Milk"])

        self.assertEqual(result, [self.expected_recipe])

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_passes_ingredients_as_comma_joined_string(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        find_recipes_by_ingredients(["Flour", "Milk", "Eggs"])

        sent_ingredients = mock_get.call_args.kwargs["params"]["ingredients"]
        self.assertEqual(sent_ingredients, "Flour,Milk,Eggs")

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_402(self, mock_get):
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 402

        with self.assertRaises(SpoonacularError) as context:
            find_recipes_by_ingredients(["Flour"])

        self.assertEqual(context.exception.status_code, 402)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_non_200_response(self, mock_get):
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 500

        with self.assertRaises(SpoonacularError) as context:
            find_recipes_by_ingredients(["Flour"])

        self.assertEqual(context.exception.status_code, 500)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout

        with self.assertRaises(SpoonacularError) as context:
            find_recipes_by_ingredients(["Flour"])

        self.assertIn("timed out", str(context.exception))

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_network_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("unreachable")

        with self.assertRaises(SpoonacularError) as context:
            find_recipes_by_ingredients(["Flour"])

        self.assertIn("Could not reach", str(context.exception))

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_returns_empty_list_when_api_returns_no_results(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        result = find_recipes_by_ingredients(["UnknownIngredient"])

        self.assertEqual(result, [])

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_recipe_without_image_defaults_to_empty_string(self, mock_get):
        api_response = [{**self.sample_api_response[0]}]
        del api_response[0]["image"]
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = api_response

        result = find_recipes_by_ingredients(["Flour"])

        self.assertEqual(result[0]["image"], "")


class RecipeDetailServiceTest(TestCase):

    def setUp(self):
        self.sample_api_response = {
            "id": 42,
            "title": "Spaghetti Bolognese",
            "image": "https://example.com/spag.jpg",
            "readyInMinutes": 60,
            "preparationMinutes": 15,
            "cookingMinutes": 45,
            "nutrition": {
                "nutrients": [
                    {"name": "Calories",      "amount": 550,  "unit": "kcal"},
                    {"name": "Fat",           "amount": 20,   "unit": "g"},
                    {"name": "Carbohydrates", "amount": 70,   "unit": "g"},
                    {"name": "Protein",       "amount": 30,   "unit": "g"},
                    {"name": "Vitamin C",     "amount": 10,   "unit": "mg"},   # not a key nutrient, for testing filter
                ]
            },
            "analyzedInstructions": [
                {
                    "name": "",
                    "steps": [
                        {"number": 1, "step": "Boil the pasta."},
                        {"number": 2, "step": "Brown the mince."},
                    ],
                }
            ],
        }

    @override_settings(SPOONACULAR_API_KEY="")
    def test_raises_when_api_key_is_not_configured(self):
        with self.assertRaises(SpoonacularError) as context:
            get_recipe_details(42)
        self.assertIn("API key", str(context.exception))

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_returns_recipe_details_on_success(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.sample_api_response

        result = get_recipe_details(42)

        self.assertEqual(result["id"], 42)
        self.assertEqual(result["title"], "Spaghetti Bolognese")
        self.assertEqual(result["ready_in_minutes"], 60)
        self.assertEqual(result["prep_minutes"], 15)
        self.assertEqual(result["cook_minutes"], 45)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_returns_only_key_nutrients(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.sample_api_response

        result = get_recipe_details(42)

        returned_names = {n["name"] for n in result["nutrition"]}
        self.assertIn("Calories", returned_names)
        self.assertIn("Protein",  returned_names)
        self.assertNotIn("Vitamin C", returned_names)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_returns_instructions_in_order(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.sample_api_response

        result = get_recipe_details(42)

        self.assertEqual(len(result["instructions"]), 2)
        self.assertEqual(result["instructions"][0]["number"], 1)
        self.assertEqual(result["instructions"][0]["step"], "Boil the pasta.")

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_sentinel_minus_one_prep_cook_returns_none(self, mock_get):
        data = {**self.sample_api_response, "preparationMinutes": -1, "cookingMinutes": -1}
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = data

        result = get_recipe_details(42)

        self.assertIsNone(result["prep_minutes"])
        self.assertIsNone(result["cook_minutes"])

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_404(self, mock_get):
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 404

        with self.assertRaises(SpoonacularError) as context:
            get_recipe_details(99999)

        self.assertEqual(context.exception.status_code, 404)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_402(self, mock_get):
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 402

        with self.assertRaises(SpoonacularError) as context:
            get_recipe_details(42)

        self.assertEqual(context.exception.status_code, 402)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_raises_spoonacular_error_on_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout

        with self.assertRaises(SpoonacularError) as context:
            get_recipe_details(42)

        self.assertIn("timed out", str(context.exception))

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_empty_instructions_returns_empty_list(self, mock_get):
        data = {**self.sample_api_response, "analyzedInstructions": []}
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = data

        result = get_recipe_details(42)

        self.assertEqual(result["instructions"], [])

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_missing_nutrition_returns_empty_list(self, mock_get):
        data = self.sample_api_response.copy()
        del data["nutrition"]
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = data

        result = get_recipe_details(42)

        self.assertEqual(result["nutrition"], [])
