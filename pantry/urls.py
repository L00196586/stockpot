from django.urls import path
from .views import (
    CookbookDeleteView,
    CookbookListCreateView,
    IngredientListCreateView,
    RecipeDetailView,
    RecipeMatchView,
    StockItemListCreateView,
    StockItemDetailView,
)

urlpatterns = [
    path("ingredients/", IngredientListCreateView.as_view(), name="ingredient-list-create"),
    path("stock/", StockItemListCreateView.as_view(), name="stock-list-create"),
    path("stock/<int:pk>/", StockItemDetailView.as_view(), name="stock-detail"),
    path("recipes/match/", RecipeMatchView.as_view(), name="recipe-match"),
    path("recipes/<int:recipe_id>/", RecipeDetailView.as_view(), name="recipe-detail"),
    path("cookbook/", CookbookListCreateView.as_view(), name="cookbook-list-create"),
    path("cookbook/<int:recipe_id>/", CookbookDeleteView.as_view(), name="cookbook-delete"),
]
