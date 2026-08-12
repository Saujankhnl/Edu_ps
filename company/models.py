from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Company(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('bid_submitter', 'Bid Submitter'),
        ('viewer', 'Viewer'),
    )

    VERIFICATION_STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin', help_text="Role of the user within the company.")
    company_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    website = models.URLField(blank=True, verbose_name="Website URL")
    description = models.TextField(blank=True, verbose_name="About the Company")
    profile_picture = models.ImageField(upload_to='company_logos/', null=True, blank=True, verbose_name="Company Logo")
    is_approved = models.BooleanField(default=False, help_text="Designates whether the company has been approved by a system admin.")

    # Verification Fields
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='not_submitted')
    registration_certificate = models.FileField(_("Company Registration Certificate"), upload_to='company_verification/', blank=True, null=True, help_text=_("Upload the official company registration certificate."))
    registration_number = models.CharField(_("Registration Number"), max_length=100, blank=True, help_text=_("Enter the official company registration number."))
    pan_number = models.CharField(_("PAN/VAT Number"), max_length=20, blank=True, help_text=_("Enter the company's PAN or VAT number."))
    verification_remarks = models.TextField(_("Admin Verification Remarks"), blank=True, help_text=_("Remarks from the admin regarding verification status."))

    def __str__(self):
        return self.company_name
