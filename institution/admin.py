from django.contrib import admin
from .models import Institution, InstitutionUser

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Institution model.
    """
    list_display = ('institution_name', 'email', 'is_approved', 'verification_status', 'institution_type')
    list_filter = ('is_approved', 'verification_status', 'institution_type')
    search_fields = ('institution_name', 'email', 'registration_number', 'pan_number')
    list_editable = ('is_approved', 'verification_status')
    list_per_page = 20
    ordering = ('-id',)

@admin.register(InstitutionUser)
class InstitutionUserAdmin(admin.ModelAdmin):
    """
    Admin configuration for the InstitutionUser model.
    """
    list_display = ('get_username', 'get_institution_name', 'role', 'get_user_email')
    list_filter = ('role', 'institution__institution_name')
    search_fields = ('user__username', 'user__email', 'institution__institution_name')
    list_editable = ('role',)
    list_per_page = 25
    ordering = ('-user__date_joined',)

    @admin.display(description='Username', ordering='user__username')
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description='Institution', ordering='institution__institution_name')
    def get_institution_name(self, obj):
        return obj.institution.institution_name

    @admin.display(description='Email', ordering='user__email')
    def get_user_email(self, obj):
        return obj.user.email

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'institution')
