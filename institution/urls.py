from django.urls import path
from . import views

app_name = "institution"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("users/", views.manage_users, name="manage_users"),
    path("users/create/", views.create_user, name="create_user"),
    path("users/edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    # Tender Management
    path("tenders/", views.list_tenders, name="list_tenders"),
    path("tenders/create/", views.create_tender, name="create_tender"),
    path("tenders/<int:tender_id>/", views.tender_detail, name="tender_detail"),
    path("tenders/<int:tender_id>/update-status/", views.update_tender_status, name="update_tender_status"),
    path('tenders/archived/', views.list_archived_tenders, name='list_archived_tenders'),
    # Institution Profile URLs
    path('profile/edit/', views.edit_institution_profile, name='edit_profile'),
    path('<int:institution_id>/profile/', views.institution_profile, name='profile'),
    # User Profile & Settings
    path('user-profile/', views.user_profile, name='user_profile'),
    path('user-profile/edit/', views.edit_user_profile, name='edit_user_profile'),
    path('user-profile/change-password/', views.change_password, name='change_password'),
]