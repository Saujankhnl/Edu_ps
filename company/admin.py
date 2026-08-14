from django.contrib import admin
from .models import Company
from django.db.models import Count

class CompanyEntity(Company):
    """Proxy model to represent a unique company entity in the admin."""
    class Meta:
        proxy = True
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

@admin.register(CompanyEntity)
class CompanyEntityAdmin(admin.ModelAdmin):
    """
    Admin view for managing unique company entities.
    This groups all user profiles by their `company_name`.
    """
    list_display = ('company_name', 'get_admin_email', 'get_user_count', 'is_approved', 'verification_status')
    list_filter = ('is_approved', 'verification_status')
    search_fields = ('company_name', 'email')
    ordering = ('company_name',)
    list_per_page = 20

    # This method is crucial for returning actual model instances, not dictionaries.
    # It ensures that only one representative Company object is shown per unique company_name.
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Get the IDs of one representative Company instance for each unique company_name.
        # Prioritize the 'admin' role if available, otherwise pick any.
        unique_company_names = qs.values_list('company_name', flat=True).distinct()
        representative_ids = []
        for name in unique_company_names:
            # Try to find the admin profile for this company_name
            representative = qs.filter(company_name=name, role='admin').first() or qs.filter(company_name=name).first()
            if representative:
                representative_ids.append(representative.id)
        return qs.filter(id__in=representative_ids).order_by('company_name')

    @admin.display(description='Admin Email')
    def get_admin_email(self, obj):
        # obj is now a Company model instance.
        admin = Company.objects.filter(company_name=obj.company_name, role='admin').first()
        return admin.email if admin else 'N/A'

    @admin.display(description='User Count')
    def get_user_count(self, obj):
        # obj is now a Company model instance, so we count users for its company_name
        return Company.objects.filter(company_name=obj.company_name).count()

@admin.register(Company)
class CompanyUserAdmin(admin.ModelAdmin):
    """Admin configuration for individual Company User profiles."""
    list_display = ('get_username', 'company_name', 'role', 'get_user_email', 'is_approved', 'verification_status')
    list_filter = ('company_name', 'role', 'is_approved', 'verification_status')
    search_fields = ('user__username', 'user__email', 'company_name')
    list_editable = ('role', 'is_approved', 'verification_status')
    list_per_page = 20
    ordering = ('company_name', 'user__username')

    @admin.display(description='Username', ordering='user__username')
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description='Email', ordering='user__email')
    def get_user_email(self, obj):
        return obj.user.email