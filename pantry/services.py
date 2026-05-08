import hashlib
import requests
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import CachedRecipe

SPOONACULAR_BASE_URL = "https://api.spoonacular.com"
# Timeout in seconds
TIMEOUT = 10
# Nutrients surfaced on the recipe detail page.
KEY_NUTRIENTS = {"Calories", "Fat", "Carbohydrates", "Protein", "Fiber", "Sugar", "Sodium"}
# Maps UserProfile dietary_preference keys to Spoonacular API parameters.
SPOONACULAR_DIET_MAP = {
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "keto": "ketogenic",
}
SPOONACULAR_INTOLERANCE_MAP = {
    "gluten_free": "gluten",
    "dairy_free": "dairy",
    "nut_free": "tree nut,peanut",
}


class SpoonacularError(Exception):
    """
    Raised when the Spoonacular API returns an unexpected response.
    """
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _build_diet_params(diets: list[str]) -> dict:
    """
    Convert a list of UserProfile dietary preference keys into Spoonacular
    request parameters for the complexSearch endpoint.

    Returns a dict with zero or more of: {"diet": "...", "intolerances": "..."}.
    """
    diet_values = sorted({
        SPOONACULAR_DIET_MAP[d]
        for d in diets if d in SPOONACULAR_DIET_MAP
    })
    intolerance_values = sorted({
        v.strip()
        for d in diets if d in SPOONACULAR_INTOLERANCE_MAP
        for v in SPOONACULAR_INTOLERANCE_MAP[d].split(",")
    })
    params = {}
    if diet_values:
        params["diet"] = ",".join(diet_values)
    if intolerance_values:
        params["intolerances"] = ",".join(intolerance_values)
    return params


def _search_cache_key(ingredient_names: list[str], diets: list[str] | None) -> str:
    """
    Build a cache key for an ingredient search

    The key is an MD5 hash of the sorted ingredients and sorted diets so that
    the same query always maps to the same key regardless of input order
    """
    parts = sorted(ingredient_names)
    if diets:
        parts.append("diets:" + ",".join(sorted(diets)))
    hex_digest = hashlib.md5("|".join(parts).encode(), usedforsecurity=False).hexdigest()
    return f"recipe_search:{hex_digest}"


def _recalculate_used_missed(results: list[dict], full_pantry_names: list[str] | None) -> list[dict]:
    """
    When only a subset of pantry ingredients is sent to Spoonacular, the API
    will classify pantry items that weren't included in the query as "missed"
    This function corrects the used/missed count by checking
    each recipe's missed_ingredients against the user's full pantry.

    If `full_pantry_names` is None (meaning the full pantry was already sent to
    Spoonacular), the results are returned unchanged.
    """
    if not full_pantry_names:
        return results

    full_set = {name.lower() for name in full_pantry_names}
    adjusted = []
    for recipe in results:
        used = list(recipe["used_ingredients"])
        missed = []
        for name in recipe["missed_ingredients"]:
            if name.lower() in full_set:
                used.append(name)
            else:
                missed.append(name)
        adjusted.append({
            **recipe,
            "used_ingredients": used,
            "missed_ingredients": missed,
            "used_count": len(used),
            "missed_count": len(missed),
        })
    return adjusted


def find_recipes_by_ingredients(
    ingredient_names: list[str],
    number: int = 12,
    diets: list[str] | None = None,
    full_pantry_names: list[str] | None = None,
) -> list[dict]:
    """
    Request to Spoonacular API for recipes suggested by the provided ingredient names and optional dietary filters.

    When `diets` is empty or None, uses Spoonacular /recipes/findByIngredients.
    When `diets` is provided, switches to /recipes/complexSearch with
    `fillIngredients=true` so the same used/missed ingredient counts are returned.

    Args:
        ingredient_names  - List of selected ingredient names from the user's pantry.
        number            - Maximum number of recipes to return (defaults to 12).
        diets             - Optional list of UserProfile dietary preference keys
                            (e.g. ["vegan", "gluten_free"]).
        full_pantry_names - When `ingredient_names` is a subset of the user's
                            pantry, pass the full list here so that used/missed
                            counts are recalculated against the complete inventory
                            rather than only the selected ingredients.

    Returns a list of recipe dicts, each containing:
            id, title, image, used_count, missed_count,
            used_ingredients (list of names), missed_ingredients (list of names)

    Raises a SpoonacularError if the API key is missing, the API is unreachable, or the API returns a non-200 response.
    """

    api_key = settings.SPOONACULAR_API_KEY
    if not api_key:
        raise SpoonacularError("Spoonacular API key is not configured. Set SPOONACULAR_API_KEY in your environment.")

    # Check for cached result before making API request
    cache_key = _search_cache_key(ingredient_names, diets)
    cached = cache.get(cache_key)
    if cached is not None:
        return _recalculate_used_missed(cached, full_pantry_names)

    use_complex_search = bool(diets)

    if use_complex_search:
        url = f"{SPOONACULAR_BASE_URL}/recipes/complexSearch"
        params = {
            "includeIngredients": ",".join(ingredient_names),
            "fillIngredients": True,
            "number": number,
            "ranking": 2,       # Spoonacular option to minimise missing ingredients
            "apiKey": api_key,
            **_build_diet_params(diets),
        }
    else:
        url = f"{SPOONACULAR_BASE_URL}/recipes/findByIngredients"
        params = {
            "ingredients": ",".join(ingredient_names),
            "number": number,
            "ranking": 2,       # Spoonacular option to minimise missing ingredients
            "ignorePantry": True,
            "apiKey": api_key,
        }

    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        raise SpoonacularError("The recipe service timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise SpoonacularError(f"Could not reach the recipe service: {e}")

    if response.status_code == 402:
        raise SpoonacularError("Recipe API quota exceeded. Please try again later.", status_code=402)

    if not response.ok:
        raise SpoonacularError(
            f"Recipe service returned an error (HTTP {response.status_code}).",
            status_code=response.status_code,
        )

    raw = response.json()
    # complexSearch wraps results, findByIngredients returns a bare list.
    items = raw.get("results", raw) if isinstance(raw, dict) else raw

    results = [
        {
            "id": item["id"],
            "title": item["title"],
            "image": item.get("image", ""),
            "used_count": item.get("usedIngredientCount", 0),
            "missed_count": item.get("missedIngredientCount", 0),
            "used_ingredients": [i["name"] for i in item.get("usedIngredients", [])],
            "missed_ingredients": [i["name"] for i in item.get("missedIngredients", [])],
        }
        for item in items
    ]

    # Store result on cache for the defined time on SEARCH_CACHE_TTL
    cache.set(cache_key, results, timeout=settings.SEARCH_CACHE_TTL)

    return _recalculate_used_missed(results, full_pantry_names)


def get_recipe_details(recipe_id: int) -> dict:
    """
    Returns detail data for a single Spoonacular recipe

    Uses the local CachedRecipe table with the following strategy:
      1. If a CachedRecipe row exists and is within RECIPE_DETAIL_CACHE_DAYS, return it
      2. Otherwise fetch from the Spoonacular API
      3. Insert/Update the result into CachedRecipe and return the fresh data

    Args:
        recipe_id   - Spoonacular recipe ID.

    Returns a dict containing:
        id, title, image, ready_in_minutes, prep_minutes, cook_minutes,
        nutrition (list of {name, amount, unit} for key nutrients),
        instructions (list of {number, step})

    Raises a SpoonacularError if the API key is missing, the recipe is not found,
    the API is unreachable, or the API returns a non-200 response.
    """

    # Check for CachedRecipe before making API request
    cutoff = timezone.now() - timedelta(days=settings.RECIPE_DETAIL_CACHE_DAYS)
    cached = CachedRecipe.objects.filter(recipe_id=recipe_id, cached_at__gte=cutoff).first()
    if cached:
        return cached.to_detail_dict()

    api_key = settings.SPOONACULAR_API_KEY
    if not api_key:
        raise SpoonacularError("Spoonacular API key is not configured. Set SPOONACULAR_API_KEY in your environment.")

    try:
        response = requests.get(
            f"{SPOONACULAR_BASE_URL}/recipes/{recipe_id}/information",
            params={"includeNutrition": True, "apiKey": api_key},
            timeout=TIMEOUT,
        )
    except requests.exceptions.Timeout:
        raise SpoonacularError("The recipe service timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise SpoonacularError(f"Could not reach the recipe service: {e}")

    if response.status_code == 402:
        raise SpoonacularError("Recipe API quota exceeded. Please try again later.", status_code=402)

    if response.status_code == 404:
        raise SpoonacularError("Recipe not found.", status_code=404)

    if not response.ok:
        raise SpoonacularError(
            f"Recipe service returned an error (HTTP {response.status_code}).",
            status_code=response.status_code,
        )

    data = response.json()

    nutrients = [
        {"name": n["name"], "amount": n["amount"], "unit": n["unit"]}
        for n in data.get("nutrition", {}).get("nutrients", [])
        if n["name"] in KEY_NUTRIENTS
    ]

    instructions = [
        {"number": step["number"], "step": step["step"]}
        for section in data.get("analyzedInstructions", [])
        for step in section.get("steps", [])
    ]

    def _minutes(value):
        """
        Spoonacular returns '-1' instead of None. This function handles the case.
        """
        return None if value == -1 else value

    detail = {
        "id": data["id"],
        "title": data["title"],
        "image": data.get("image", ""),
        "ready_in_minutes": data.get("readyInMinutes"),
        "prep_minutes": _minutes(data.get("preparationMinutes", -1)),
        "cook_minutes": _minutes(data.get("cookingMinutes", -1)),
        "nutrition": nutrients,
        "instructions": instructions,
    }

    # Store result on cache for the defined time on SEARCH_CACHE_TTL
    CachedRecipe.objects.update_or_create(
        recipe_id=recipe_id,
        defaults={
            "title": detail["title"],
            "image": detail["image"],
            "ready_in_minutes": detail["ready_in_minutes"],
            "prep_minutes": detail["prep_minutes"],
            "cook_minutes": detail["cook_minutes"],
            "nutrition": detail["nutrition"],
            "instructions": detail["instructions"],
        },
    )

    return detail
