from django.urls import path
from . import views

app_name = "tenders"
urlpatterns = [
    path("create/", views.create_tender, name="create_tender"),
    path("list/", views.list_tenders, name="list_tenders"),
    path("archived/", views.list_archived_tenders, name="list_archived_tenders"),
    path("for-approval/", views.list_for_approval, name="list_for_approval"),
    path("<int:tender_id>/edit/", views.edit_tender, name="edit_tender"),
    path("<int:tender_id>/delete/", views.delete_tender, name="delete_tender"),
    path("<int:tender_id>/", views.tender_detail, name="tender_detail"),
    path(
        "<int:tender_id>/update_status/",
        views.update_tender_status,
        name="update_tender_status",
    ),
    # Bidding URLs
    path("<int:tender_id>/submit-bid/", views.submit_bid, name="submit_bid"),
    path("my-bids/", views.my_bids, name="my_bids"),
    path("bids/<int:bid_id>/", views.bid_detail, name="bid_detail"),
    path("bids/<int:bid_id>/update_status/", views.update_bid_status, name="update_bid_status"),
]