from django.urls import path
from . import views

app_name = "institution"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("users/", views.manage_users, name="manage_users"),
]