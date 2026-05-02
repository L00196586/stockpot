from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated

from .models import Ingredient, StockItem
from .serializers import IngredientSerializer, StockItemReadSerializer, StockItemWriteSerializer
from django.views.generic import TemplateView


class IngredientListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/ingredients/ — Returns a JSON list of all Ingredients objects.
    POST /api/ingredients/ — Add a new Ingredient.
    """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class StockItemListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/stock/ — Returns a JSON list of all StockItem objects belonging to the logged-in User.
    POST /api/stock/ — Add a new StockItem to the User's pantry.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            StockItem.objects.filter(user=self.request.user)
            .select_related("ingredient")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StockItemWriteSerializer
        return StockItemReadSerializer


class StockItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/stock/<id>/ — Retrieve a single StockItem.
    PUT    /api/stock/<id>/ — Replace a StockItem quantity and expiry date.
    PATCH  /api/stock/<id>/ — Partially update a StockItem.
    DELETE /api/stock/<id>/ — Remove an StockItem entirely.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StockItem.objects.filter(user=self.request.user).select_related("ingredient")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return StockItemWriteSerializer
        return StockItemReadSerializer


class PantryPageView(TemplateView):
    """
    GET /pantry/
    My Stock dashboard HTML page.
    """
    template_name = "pantry/stock.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unit_choices"] = Ingredient.Unit.choices
        return context
