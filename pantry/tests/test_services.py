from unittest.mock import patch

import requests
from django.test import TestCase, override_settings
from pantry.services import SpoonacularError, find_recipes_by_ingredients


class SpoonacularServiceTest(TestCase):

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
