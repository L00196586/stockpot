from django.contrib import admin
from .models import Ingredient, StockItem


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ["user", "ingredient", "unit", "quantity", "expiry_date", "updated_at"]
    list_filter = ["unit", "expiry_date"]
    search_fields = ["user__username", "ingredient__name"]
    ordering = ["user", "ingredient__name"]
