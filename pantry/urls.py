from django.urls import path
from .views import IngredientListCreateView, StockItemListCreateView, StockItemDetailView

urlpatterns = [
    path("ingredients/", IngredientListCreateView.as_view(), name="ingredient-list-create"),
    path("stock/", StockItemListCreateView.as_view(), name="stock-list-create"),
    path("stock/<int:pk>/", StockItemDetailView.as_view(), name="stock-detail"),
]
