from django.contrib import admin
from django.urls import path, include
from users.views import LoginPageView, ProfilePageView, RegisterPageView
from pantry.views import FavouritesPageView, PantryPageView, RecipeDetailPageView, RecipeSuggestionsPageView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/", include("pantry.urls")),
    path("api/auth/", include("users.urls")),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("login/", LoginPageView.as_view(), name="login-page"),
    path("profile/", ProfilePageView.as_view(), name="profile-page"),
    path("pantry/", PantryPageView.as_view(), name="pantry-page"),
    path("recipes/", RecipeSuggestionsPageView.as_view(), name="recipes-page"),
    path("recipes/<int:recipe_id>/", RecipeDetailPageView.as_view(), name="recipe-detail-page"),
    path("favourites/", FavouritesPageView.as_view(), name="favourites-page"),
]
