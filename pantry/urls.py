from django.urls import path
from .views import IngredientListCreateView, RecipeDetailView, RecipeMatchView, StockItemListCreateView, StockItemDetailView

urlpatterns = [
    path("ingredients/", IngredientListCreateView.as_view(), name="ingredient-list-create"),
    path("stock/", StockItemListCreateView.as_view(), name="stock-list-create"),
    path("stock/<int:pk>/", StockItemDetailView.as_view(), name="stock-detail"),
    path("recipes/match/", RecipeMatchView.as_view(), name="recipe-match"),
    path("recipes/<int:recipe_id>/", RecipeDetailView.as_view(), name="recipe-detail"),
]
