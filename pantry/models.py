from django.db import models
from django.contrib.auth.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockItem(models.Model):
    class Unit(models.TextChoices):
        GRAMS = "g", "Grams"
        KILOGRAMS = "kg", "Kilograms"
        MILLILITRES = "ml", "Millilitres"
        LITRES = "L", "Litres"
        PIECES = "pcs", "Pieces"
        TABLESPOONS = "tbsp", "Tablespoons"
        TEASPOONS = "tsp", "Teaspoons"
        CUPS = "cup", "Cups"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stock_items")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="stock_items")
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.GRAMS)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "ingredient")
        ordering = ["ingredient__name"]

    def __str__(self):
        return f"{self.user.username} – {self.ingredient.name}: {self.quantity}{self.unit}"


class SavedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_recipes")
    recipe_id = models.IntegerField()
    title = models.CharField(max_length=500)
    image = models.URLField(blank=True, default="")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "recipe_id")
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.user.username} – {self.title}"


class CachedRecipe(models.Model):
    """
    Local cache for Spoonacular recipe detail data.

    Records are considered fresh for RECIPE_DETAIL_CACHE_DAYS days.  After that
    the service layer will re-fetch from the API and update this row in place.
    """

    recipe_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=500)
    image = models.URLField(blank=True, default="")
    ready_in_minutes = models.IntegerField(null=True, blank=True)
    prep_minutes = models.IntegerField(null=True, blank=True)
    cook_minutes = models.IntegerField(null=True, blank=True)
    # Stored as a list of {name, amount, unit} dicts.
    nutrition = models.JSONField(default=list)
    # Stored as a list of {number, step} dicts.
    instructions = models.JSONField(default=list)
    # Updated every time the record is refreshed from the API.
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["recipe_id"]

    def __str__(self):
        return f"CachedRecipe({self.recipe_id}: {self.title})"

    def to_detail_dict(self) -> dict:
        """Return the same structure that get_recipe_details() produces."""
        return {
            "id": self.recipe_id,
            "title": self.title,
            "image": self.image,
            "ready_in_minutes": self.ready_in_minutes,
            "prep_minutes": self.prep_minutes,
            "cook_minutes": self.cook_minutes,
            "nutrition": self.nutrition,
            "instructions": self.instructions,
        }
