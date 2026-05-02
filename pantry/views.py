from rest_framework import generics, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ingredient, SavedRecipe, StockItem
from .serializers import IngredientSerializer, SavedRecipeSerializer, StockItemReadSerializer, StockItemWriteSerializer
from .services import SpoonacularError, find_recipes_by_ingredients, get_recipe_details
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


class RecipeMatchView(APIView):
    """
    GET /api/recipes/match/
    Returns recipe suggestions from Spoonacular based on the user's current pantry.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ingredient_names = list(
            StockItem.objects.filter(user=request.user)
            .select_related("ingredient")
            .values_list("ingredient__name", flat=True)
        )

        if not ingredient_names:
            return Response(
                {"detail": "Your pantry is empty. Add some ingredients to get recipe suggestions."},
                status=status.HTTP_200_OK,
            )

        try:
            recipes = find_recipes_by_ingredients(ingredient_names)
        except SpoonacularError as e:
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            if e.status_code == 402:
                http_status = status.HTTP_429_TOO_MANY_REQUESTS
            return Response({"detail": str(e)}, status=http_status)

        return Response(recipes, status=status.HTTP_200_OK)


class RecipeSuggestionsPageView(TemplateView):
    """
    GET /recipes/
    Recipe suggestions HTML page.
    """
    template_name = "pantry/recipes.html"


class RecipeDetailView(APIView):
    """
    GET /api/recipes/<recipe_id>/
    Returns details for a single recipe.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, recipe_id):
        try:
            details = get_recipe_details(recipe_id)
        except SpoonacularError as e:
            if e.status_code == 402:
                http_status = status.HTTP_429_TOO_MANY_REQUESTS
            elif e.status_code == 404:
                http_status = status.HTTP_404_NOT_FOUND
            else:
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response({"detail": str(e)}, status=http_status)

        return Response(details, status=status.HTTP_200_OK)


class RecipeDetailPageView(TemplateView):
    """
    GET /recipes/<recipe_id>/
    Recipe detail HTML page.
    """
    template_name = "pantry/recipe_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe_id"] = kwargs.get("recipe_id")
        return context


class FavouriteListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/favourites/ — List the authenticated user's saved recipes.
    POST /api/favourites/ — Save a recipe to favourites.
    """
    serializer_class = SavedRecipeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedRecipe.objects.filter(user=self.request.user)


class FavouriteDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/favourites/<recipe_id>/ — Remove a recipe from favourites by Spoonacular recipe ID.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        recipe_id = self.kwargs["recipe_id"]
        return generics.get_object_or_404(
            SavedRecipe, user=self.request.user, recipe_id=recipe_id
        )

