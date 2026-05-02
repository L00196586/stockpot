import requests
from django.conf import settings

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


def find_recipes_by_ingredients(
    ingredient_names: list[str],
    number: int = 12,
    diets: list[str] | None = None,
) -> list[dict]:
    """
    Request to Spoonacular API for recipes suggested by the provided ingredient names and optional dietary filters.

    When `diets` is empty or None, uses Spoonacular /recipes/findByIngredients.
    When `diets` is provided, switches to /recipes/complexSearch with
    `fillIngredients=true` so the same used/missed ingredient counts are returned.

    Args:
        ingredient_names  - List of ingredient name strings from the user's pantry.
        number            - Maximum number of recipes to return (defaults to 12).
        diets             - Optional list of UserProfile dietary preference keys
                            (e.g. ["vegan", "gluten_free"]).

    Returns a list of recipe dicts, each containing:
            id, title, image, used_count, missed_count,
            used_ingredients (list of names), missed_ingredients (list of names)

    Raises a SpoonacularError if the API key is missing, the API is unreachable, or the API returns a non-200 response.
    """

    api_key = settings.SPOONACULAR_API_KEY
    if not api_key:
        raise SpoonacularError("Spoonacular API key is not configured. Set SPOONACULAR_API_KEY in your environment.")

    use_complex_search = bool(diets)

    if use_complex_search:
        url = f"{SPOONACULAR_BASE_URL}/recipes/complexSearch"
        params = {
            "includeIngredients": ",".join(ingredient_names),
            "fillIngredients": True,
            "number": number,
            "ranking": 1,       # Spoonacular option to maximise used ingredients
            "apiKey": api_key,
            **_build_diet_params(diets),
        }
    else:
        url = f"{SPOONACULAR_BASE_URL}/recipes/findByIngredients"
        params = {
            "ingredients": ",".join(ingredient_names),
            "number": number,
            "ranking": 1,       # Spoonacular option to maximise used ingredients
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

    return [
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


def get_recipe_details(recipe_id: int) -> dict:
    """
    Request to Spoonacular /recipes/{id}/information endpoint.

    Args:
        recipe_id   - Spoonacular recipe ID.

    Returns a dict containing:
        id, title, image, ready_in_minutes, prep_minutes, cook_minutes,
        nutrition (list of {name, amount, unit} for key nutrients),
        instructions (list of {number, step})

    Raises a SpoonacularError if the API key is missing, the recipe is not found,
    the API is unreachable, or the API returns a non-200 response.
    """
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

    return {
        "id": data["id"],
        "title": data["title"],
        "image": data.get("image", ""),
        "ready_in_minutes": data.get("readyInMinutes"),
        "prep_minutes": _minutes(data.get("preparationMinutes", -1)),
        "cook_minutes": _minutes(data.get("cookingMinutes", -1)),
        "nutrition": nutrients,
        "instructions": instructions,
    }
