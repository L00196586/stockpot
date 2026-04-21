from django.db import models
from django.contrib.auth.models import User


class Ingredient(models.Model):
    class Unit(models.TextChoices):
        GRAMS = "g", "Grams"
        KILOGRAMS = "kg", "Kilograms"
        MILLILITRES = "ml", "Millilitres"
        LITRES = "L", "Litres"
        PIECES = "pcs", "Pieces"
        TABLESPOONS = "tbsp", "Tablespoons"
        TEASPOONS = "tsp", "Teaspoons"
        CUPS = "cup", "Cups"

    name = models.CharField(max_length=200, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.GRAMS)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.unit})"


class StockItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stock_items")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="stock_items")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "ingredient")
        ordering = ["ingredient__name"]

    def __str__(self):
        return f"{self.user.username} – {self.ingredient.name}: {self.quantity}{self.ingredient.unit}"
