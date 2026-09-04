from django.urls import path
from . import views

app_name = "company"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.company_profile, name="company_profile"),
    path("my-profile/", views.user_profile, name="user_profile"),
    path("my-profile/edit/", views.edit_user_profile, name="edit_user_profile"),
    path("profile/edit/", views.edit_company_profile, name="edit_company_profile"),
    path("change-password/", views.change_password, name="change_password"),
    path("tenders/", views.list_published_tenders, name="list_published_tenders"),
    path("analytics/", views.analytics_reports, name="analytics_reports"),
    path("analytics/pdf/", views.generate_analytics_pdf, name="generate_analytics_pdf"),
    path('verification/', views.verification_submission, name='verification'),
 
    path("manage-users/", views.manage_users, name="manage_users"),
    path("manage-users/create/", views.create_company_user, name="create_user"),
    path("manage-users/edit/<int:user_id>/", views.edit_company_user, name="edit_user"),
    path("manage-users/delete/<int:user_id>/", views.delete_company_user, name="delete_user"),
]