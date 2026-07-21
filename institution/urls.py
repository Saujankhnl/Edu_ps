from django.urls import path
from . import views

app_name = "institution"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("users/", views.manage_users, name="manage_users"),
    path("users/create/", views.create_user, name="create_user"),
    path("users/edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    # Institution Profile URLs
    path('profile/edit/', views.edit_institution_profile, name='edit_profile'),
    path('<int:institution_id>/profile/', views.institution_profile, name='profile'),
    # User Profile & Settings
    path('user-profile/', views.user_profile, name='user_profile'),
    path('user-profile/edit/', views.edit_user_profile, name='edit_user_profile'),
    path('user-profile/change-password/', views.change_password, name='change_password'),
    # Reporting URLs
    path('reports/institution/', views.institution_report, name='institution_report'),
    path('reports/institution/pdf/', views.generate_report_pdf, name='generate_report_pdf'),
]