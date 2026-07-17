from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.company_profile, name='company_profile'),
    path('profile/edit/', views.edit_company_profile, name='edit_company_profile'),
    path('change-password/', views.change_password, name='change_password'), # This line was already correct
    path('tenders/', views.list_published_tenders, name='list_published_tenders'),
    path('analytics/', views.analytics_reports, name='analytics_reports'),
]