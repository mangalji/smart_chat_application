from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_request, name="signup"),
    path("signup/verify/", views.signup_verify, name="signup_verify"),
    path("login/", views.login_request, name="login"),
    path("login/verify/", views.login_verify, name="login_verify"),
    path("logout/", views.logout_view, name="logout"),
]
