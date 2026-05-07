from unittest.mock import patch

import requests
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from pantry.services import (
    SpoonacularError,
    _build_diet_params,
    _search_cache_key,
    find_recipes_by_ingredients,
    get_recipe_details,
)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
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


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
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


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
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


class SearchCacheKeyTest(TestCase):

    def test_same_ingredients_produce_same_key(self):
        k1 = _search_cache_key(["Flour", "Milk"], None)
        k2 = _search_cache_key(["Flour", "Milk"], None)
        self.assertEqual(k1, k2)

    def test_same_ingredient_different_order_produce_same_key(self):
        k1 = _search_cache_key(["Flour", "Milk"], None)
        k2 = _search_cache_key(["Milk", "Flour"], None)
        self.assertEqual(k1, k2)

    def test_different_ingredients_produce_different_keys(self):
        k1 = _search_cache_key(["Flour"], None)
        k2 = _search_cache_key(["Eggs"], None)
        self.assertNotEqual(k1, k2)

    def test_diets_are_included_in_key(self):
        k1 = _search_cache_key(["Flour"], None)
        k2 = _search_cache_key(["Flour"], ["vegan"])
        self.assertNotEqual(k1, k2)

    def test_same_ingredient_same_diets_different_order_produce_same_key(self):
        k1 = _search_cache_key(["Flour"], ["vegan", "gluten_free"])
        k2 = _search_cache_key(["Flour"], ["gluten_free", "vegan"])
        self.assertEqual(k1, k2)

    def test_key_has_expected_prefix(self):
        key = _search_cache_key(["Flour"], None)
        self.assertTrue(key.startswith("recipe_search:"))


@override_settings(
    SPOONACULAR_API_KEY="test-key",
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class FindRecipesByIngredientsCacheTest(TestCase):

    def setUp(self):
        cache.clear()
        self.api_response = [
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
        self.expected = [
            {
                "id": 1,
                "title": "Pancakes",
                "image": "https://example.com/pancakes.jpg",
                "used_count": 2,
                "missed_count": 1,
                "used_ingredients": ["Flour", "Milk"],
                "missed_ingredients": ["Eggs"],
            }
        ]

    def tearDown(self):
        cache.clear()

    @patch("pantry.services.requests.get")
    def test_cache_miss_calls_api_and_stores_result(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.api_response

        result = find_recipes_by_ingredients(["Flour", "Milk"])

        mock_get.assert_called_once()
        self.assertEqual(result, self.expected)

        key = _search_cache_key(["Flour", "Milk"], None)
        self.assertEqual(cache.get(key), self.expected)

    @patch("pantry.services.requests.get")
    def test_cache_hit_skips_api_call(self, mock_get):
        key = _search_cache_key(["Flour", "Milk"], None)
        cache.set(key, self.expected, timeout=60)

        result = find_recipes_by_ingredients(["Flour", "Milk"])

        mock_get.assert_not_called()
        self.assertEqual(result, self.expected)

    @patch("pantry.services.requests.get")
    def test_different_ingredients_use_different_cache_entries(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.api_response

        find_recipes_by_ingredients(["Flour"])
        find_recipes_by_ingredients(["Eggs"])

        self.assertEqual(mock_get.call_count, 2)

    @patch("pantry.services.requests.get")
    def test_api_error_does_not_populate_cache(self, mock_get):
        mock_get.return_value.ok = False
        mock_get.return_value.status_code = 500

        with self.assertRaises(SpoonacularError):
            find_recipes_by_ingredients(["Flour"])

        key = _search_cache_key(["Flour"], None)
        self.assertIsNone(cache.get(key))

    @patch("pantry.services.requests.get")
    def test_diets_param_uses_separate_cache_entry(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"results": []}

        find_recipes_by_ingredients(["Flour"])
        find_recipes_by_ingredients(["Flour"], diets=["vegan"])

        self.assertEqual(mock_get.call_count, 2)


@override_settings(
    SPOONACULAR_API_KEY="test-key",
    RECIPE_DETAIL_CACHE_DAYS=30,
)
class RecipeDetailCacheTest(TestCase):

    def setUp(self):
        from pantry.models import CachedRecipe
        self.CachedRecipe = CachedRecipe
        self.recipe_id = 42
        self.api_response = {
            "id": 42,
            "title": "Spaghetti Bolognese",
            "image": "https://example.com/spag.jpg",
            "readyInMinutes": 60,
            "preparationMinutes": 15,
            "cookingMinutes": 45,
            "nutrition": {
                "nutrients": [
                    {"name": "Calories", "amount": 550, "unit": "kcal"},
                ]
            },
            "analyzedInstructions": [
                {"name": "", "steps": [{"number": 1, "step": "Boil pasta."}]},
            ],
        }

    @patch("pantry.services.requests.get")
    def test_cache_miss_fetches_api_and_saves_to_db(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.api_response

        result = get_recipe_details(self.recipe_id)

        mock_get.assert_called_once()
        self.assertEqual(result["title"], "Spaghetti Bolognese")
        self.assertTrue(self.CachedRecipe.objects.filter(recipe_id=self.recipe_id).exists())

    @patch("pantry.services.requests.get")
    def test_fresh_db_record_skips_api_call(self, mock_get):
        self.CachedRecipe.objects.create(
            recipe_id=self.recipe_id,
            title="Spaghetti Bolognese",
            image="https://example.com/spag.jpg",
            ready_in_minutes=60,
            prep_minutes=15,
            cook_minutes=45,
            nutrition=[{"name": "Calories", "amount": 550, "unit": "kcal"}],
            instructions=[{"number": 1, "step": "Boil pasta."}],
        )

        result = get_recipe_details(self.recipe_id)

        mock_get.assert_not_called()
        self.assertEqual(result["title"], "Spaghetti Bolognese")

    @patch("pantry.services.requests.get")
    def test_stale_db_record_triggers_api_refresh(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.api_response

        record = self.CachedRecipe.objects.create(
            recipe_id=self.recipe_id,
            title="Old Title",
            nutrition=[], instructions=[],
        )
        stale_time = timezone.now() - timedelta(days=31)
        self.CachedRecipe.objects.filter(pk=record.pk).update(cached_at=stale_time)

        result = get_recipe_details(self.recipe_id)

        mock_get.assert_called_once()
        self.assertEqual(result["title"], "Spaghetti Bolognese")

    @patch("pantry.services.requests.get")
    def test_api_result_upserts_existing_record(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.api_response

        self.CachedRecipe.objects.create(
            recipe_id=self.recipe_id, title="Old Title", nutrition=[], instructions=[]
        )
        stale_time = timezone.now() - timedelta(days=31)
        self.CachedRecipe.objects.filter(recipe_id=self.recipe_id).update(cached_at=stale_time)

        get_recipe_details(self.recipe_id)

        self.assertEqual(self.CachedRecipe.objects.filter(recipe_id=self.recipe_id).count(), 1)
        updated = self.CachedRecipe.objects.get(recipe_id=self.recipe_id)
        self.assertEqual(updated.title, "Spaghetti Bolognese")

    def test_fresh_cache_returns_to_detail_dict_shape(self):
        self.CachedRecipe.objects.create(
            recipe_id=self.recipe_id,
            title="Spaghetti Bolognese",
            image="https://example.com/spag.jpg",
            ready_in_minutes=60,
            prep_minutes=15,
            cook_minutes=45,
            nutrition=[{"name": "Calories", "amount": 550, "unit": "kcal"}],
            instructions=[{"number": 1, "step": "Boil pasta."}],
        )
        result = get_recipe_details(self.recipe_id)
        expected_keys = {"id", "title", "image", "ready_in_minutes", "prep_minutes",
                         "cook_minutes", "nutrition", "instructions"}
        self.assertEqual(set(result.keys()), expected_keys)
