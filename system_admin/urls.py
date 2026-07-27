from django.urls import path
from . import views

app_name = 'system_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('institutions/pending/', views.list_pending_institutions, name='pending_institutions'),
    path('institutions/all/', views.list_all_institutions, name='all_institutions'),
    path('institutions/approve/<int:institution_id>/', views.approve_institution, name='approve_institution'),
    path('institutions/reject/<int:institution_id>/', views.reject_institution, name='reject_institution'),
    path('institutions/pending-verifications/', views.list_pending_verifications, name='pending_verifications'),
    path('institutions/verifications/<int:institution_id>/', views.process_verification, name='process_verification'),
    path('companies/pending/', views.list_pending_companies, name='pending_companies'),
    path('companies/all/', views.list_all_companies, name='all_companies'),
    path('companies/approve/<int:company_id>/', views.approve_company, name='approve_company'),
    path('companies/reject/<int:company_id>/', views.reject_company, name='reject_company'),
    path('companies/pending-verifications/', views.list_pending_company_verifications, name='pending_company_verifications'),
    path('companies/verifications/<int:company_id>/', views.process_company_verification, name='process_company_verification'),
    path('users/all/', views.manage_all_users, name='manage_all_users'),
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('tenders/monitoring/', views.tender_monitoring, name='tender_monitoring'),
    path('tenders/monitoring/pdf/', views.generate_tender_monitoring_pdf, name='generate_tender_monitoring_pdf'),
    path('bids/monitoring/', views.bid_monitoring, name='bid_monitoring'),
    path('bids/monitoring/pdf/', views.generate_bid_monitoring_pdf, name='generate_bid_monitoring_pdf'),
    path('analytics/', views.analytics_reports, name='analytics_reports'),
    path('analytics/pdf/', views.generate_analytics_pdf, name='generate_analytics_pdf'),
]