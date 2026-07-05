from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("",views.homepage,name="home"),
    path("login/",views.login_page,name="login_page"),
    path("register/",views.register,name="register"),
    path("forget-password/",views.forget_password,name="forget_password"),
    path("verify-otp/",views.verify_otp,name="verify_otp"),
    path("reset-password/",views.reset_password,name="reset_password"),

]