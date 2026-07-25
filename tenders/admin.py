from django.contrib import admin
from .models import Tender, Bid, TenderActivity

@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    """
    Admin view for Tenders.
    """
    list_display = ('title', 'institution', 'status', 'created_at', 'deadline', 'created_by')
    list_filter = ('status', 'institution', 'created_at')
    search_fields = ('title', 'description', 'institution__institution_name', 'created_by__user__username')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('title', 'institution', 'description')}),
        ('Status & Control', {'fields': ('status', 'remarks', 'created_by')}),
        ('Dates & Deadlines', {'fields': ('opening_date', 'deadline')}),
        ('Documents', {'fields': ('document',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    """
    Admin view for Bids.
    """
    list_display = ('tender', 'company', 'bid_amount', 'status', 'submitted_at')
    list_filter = ('status', 'tender__institution')
    search_fields = ('tender__title', 'company__company_name')
    date_hierarchy = 'submitted_at'
    ordering = ('-submitted_at',)

@admin.register(TenderActivity)
class TenderActivityAdmin(admin.ModelAdmin):
    """
    Admin view for Tender Activities.
    """
    list_display = ('tender', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'tender__institution')
    search_fields = ('tender__title', 'performed_by__user__username')
    readonly_fields = ('tender', 'action', 'remarks', 'performed_by', 'timestamp')