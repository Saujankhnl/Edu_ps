from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("",views.homepage,name="home"),
    path("login/",views.login_page,name="login_page"),
    path("regsiter/",views.register,name="register"),
]