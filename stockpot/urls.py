from django.contrib import admin
from django.urls import path, include
from users.views import LoginPageView, RegisterPageView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/", include("pantry.urls")),
    path("api/auth/", include("users.urls")),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("login/", LoginPageView.as_view(), name="login-page"),
]
