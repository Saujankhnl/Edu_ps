from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Institution(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    INSTITUTION_TYPE_CHOICES = [
        ('public', 'Public University/College'),
        ('private', 'Private University/College'),
        ('government', 'Government Body'),
        ('ngo', 'Non-Governmental Organization'),
        ('other', 'Other'),
    ]

    institution_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=10)
    address = models.TextField()
    profile_picture = models.ImageField(upload_to='institution_profiles/', null=True, blank=True, verbose_name="Profile Picture")
    institution_head_name = models.CharField(max_length=100, blank=True, verbose_name="Institution Head Name")
    website = models.URLField(blank=True, verbose_name="Website URL")
    description = models.TextField(blank=True, verbose_name="About the Institution")
    is_approved = models.BooleanField(default=False, help_text="Designates whether the institution has been approved by a system admin.")

    # Verification Fields
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='not_submitted'
    )
    institution_type = models.CharField(
        _("Type of Institution"), max_length=50, choices=INSTITUTION_TYPE_CHOICES, default='other', blank=True
    )
    contact_person = models.CharField(
        _("Contact Person Name"), max_length=100, blank=True
    )
    contact_person_number = models.CharField(
        _("Contact Person Number"), max_length=20, blank=True
    )
    registration_certificate = models.FileField(
        _("Registration Certificate"), upload_to='institution_verification/',
        help_text=_("Upload the official legal registration certificate.")
    )
    registration_number = models.CharField(
        _("Registration Number"), max_length=100, help_text=_("Enter the official registration number.")
    )
    pan_number = models.CharField(
        _("PAN/VAT Number"), max_length=20, help_text=_("Enter the institution's PAN or VAT number.")
    )
    pan_certificate = models.FileField(
        _("PAN/VAT Certificate (Optional)"), upload_to='institution_verification/',
        blank=True, null=True,
        help_text=_("Upload a copy of the PAN/VAT registration certificate if available.")
    )
    authorization_letter = models.FileField(
        _("Authorization Letter (Optional)"), upload_to='institution_verification/',
        blank=True, null=True,
        help_text=_("An official letter authorizing this account to act on behalf of the institution.")
    )
    verification_remarks = models.TextField(
        _("Admin Verification Remarks"), blank=True, help_text=_("Remarks from the admin regarding verification status.")
    )

    def __str__(self):
        return self.institution_name

class InstitutionUser(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Institution Admin'),
        ('creator', 'Creator'),
        ('reviewer', 'Reviewer'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_profile')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='creator')
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Phone Number")
    profile_picture = models.ImageField(upload_to='user_profiles/', null=True, blank=True, verbose_name="Profile Picture")

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} at {self.institution.institution_name}"