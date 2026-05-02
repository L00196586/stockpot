from unittest.mock import patch

import requests
from django.test import TestCase, override_settings
from pantry.services import (
    SpoonacularError,
    _build_diet_params,
    find_recipes_by_ingredients,
    get_recipe_details,
)


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


class RecipeDietaryFilteringServiceTest(TestCase):

    def test_empty_diets_returns_empty_params(self):
        self.assertEqual(_build_diet_params([]), {})

    def test_vegetarian_maps_to_diet_param(self):
        result = _build_diet_params(["vegetarian"])
        self.assertEqual(result, {"diet": "vegetarian"})

    def test_vegan_maps_to_diet_param(self):
        result = _build_diet_params(["vegan"])
        self.assertEqual(result, {"diet": "vegan"})

    def test_keto_maps_to_ketogenic(self):
        result = _build_diet_params(["keto"])
        self.assertEqual(result, {"diet": "ketogenic"})

    def test_gluten_free_maps_to_intolerance(self):
        result = _build_diet_params(["gluten_free"])
        self.assertEqual(result, {"intolerances": "gluten"})

    def test_dairy_free_maps_to_intolerance(self):
        result = _build_diet_params(["dairy_free"])
        self.assertEqual(result, {"intolerances": "dairy"})

    def test_nut_free_maps_to_two_intolerances(self):
        result = _build_diet_params(["nut_free"])
        intolerances = sorted(result["intolerances"].split(","))
        self.assertIn("peanut", intolerances)
        self.assertIn("tree nut", intolerances)

    def test_unknown_key_is_ignored(self):
        self.assertEqual(_build_diet_params(["non-existant"]), {})

    def test_mixed_diet_and_intolerance(self):
        result = _build_diet_params(["vegan", "gluten_free"])
        self.assertEqual(result["diet"], "vegan")
        self.assertEqual(result["intolerances"], "gluten")

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_uses_complex_search_endpoint_when_diets_provided(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"results": []}

        find_recipes_by_ingredients(["Flour"], diets=["vegan"])

        called_url = mock_get.call_args.args[0]
        self.assertIn("complexSearch", called_url)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_uses_find_by_ingredients_endpoint_when_no_diets(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        find_recipes_by_ingredients(["Flour"])

        called_url = mock_get.call_args.args[0]
        self.assertIn("findByIngredients", called_url)

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_complex_search_response_is_unwrapped(self, mock_get):
        api_response = {
            "results": [
                {
                    "id": 10,
                    "title": "Vegan Pasta",
                    "image": "https://example.com/pasta.jpg",
                    "usedIngredientCount": 3,
                    "missedIngredientCount": 0,
                    "usedIngredients": [{"name": "Pasta"}, {"name": "Tomato"}, {"name": "Basil"}],
                    "missedIngredients": [],
                }
            ]
        }
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = api_response

        result = find_recipes_by_ingredients(["Pasta"], diets=["vegan"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 10)
        self.assertEqual(result[0]["title"], "Vegan Pasta")

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_diet_params_are_passed_to_complex_search(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"results": []}

        find_recipes_by_ingredients(["Flour"], diets=["vegan", "gluten_free"])

        sent_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(sent_params["diet"], "vegan")
        self.assertIn("gluten", sent_params["intolerances"])

    @override_settings(SPOONACULAR_API_KEY="test-key")
    @patch("pantry.services.requests.get")
    def test_halal_kosher_do_not_add_extra_params(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"results": []}

        find_recipes_by_ingredients(["Flour"], diets=["halal", "kosher"])

        sent_params = mock_get.call_args.kwargs["params"]
        self.assertNotIn("diet", sent_params)
        self.assertNotIn("intolerances", sent_params)


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
