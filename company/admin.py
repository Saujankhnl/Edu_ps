from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Company model.
    This will display company user profiles in the Django admin site.
    """
    list_display = ('get_username', 'company_name', 'role', 'email', 'is_approved', 'verification_status')
    list_filter = ('role', 'is_approved', 'verification_status', 'company_name')
    search_fields = ('user__username', 'company_name', 'email')
    list_editable = ('is_approved', 'verification_status', 'role')
    list_per_page = 25
    ordering = ('-user__date_joined',)

    @admin.display(description='Username', ordering='user__username')
    def get_username(self, obj):
        """Returns the username from the related User object."""
        return obj.user.username

    def get_queryset(self, request):
        """
        Optimize the queryset by pre-fetching the related User object
        to reduce database queries.
        """
        return super().get_queryset(request).select_related('user')