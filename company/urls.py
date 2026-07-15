from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.company_profile, name='company_profile'),
    path('profile/edit/', views.edit_company_profile, name='edit_company_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('tenders/', views.list_published_tenders, name='list_tenders'),
    path('tenders/<int:tender_id>/', views.tender_detail, name='tender_detail'),
    path('tenders/<int:tender_id>/submit-bid/', views.submit_bid, name='submit_bid'),
    path('my-bids/', views.my_bids, name='my_bids'),
    path('my-bids/<int:bid_id>/', views.bid_detail, name='bid_detail'),
    path('analytics/', views.analytics_reports, name='analytics_reports'),
]