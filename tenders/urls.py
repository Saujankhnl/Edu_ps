from django.urls import path
from . import views

app_name = 'tenders'

urlpatterns = [
    # Tender URLs
    path('create/', views.create_tender, name='create_tender'),
    path('<int:tender_id>/', views.tender_detail, name='tender_detail'),
    path('<int:tender_id>/edit/', views.edit_tender, name='edit_tender'),
    path('<int:tender_id>/delete/', views.delete_tender, name='delete_tender'),
    path('list/', views.list_tenders, name='list_tenders'),
    path('<int:tender_id>/update-status/', views.update_tender_status, name='update_tender_status'),

    # Bid URLs
    path('<int:tender_id>/submit-bid/', views.submit_bid, name='submit_bid'),
    path('my-bids/', views.my_bids, name='my_bids'),
    path('bid/<int:bid_id>/', views.bid_detail, name='bid_detail'),
    path('bid/<int:bid_id>/update-status/', views.update_bid_status, name='update_bid_status'),
    path('bid/<int:bid_id>/review/', views.review_and_submit_bid, name='review_and_submit_bid'), # This is the missing URL

    # PDF Generation URLs
    path('<int:tender_id>/pdf/detail/', views.generate_tender_pdf, name='generate_tender_pdf'),
    path('<int:tender_id>/pdf/bids/', views.generate_bids_pdf, name='generate_bids_pdf'),
]