from django.db import models
from django.contrib.auth.models import User

class Institution(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_admin_profile')
    institution_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    # New fields for the profile
    profile_picture = models.ImageField(upload_to='institution_profiles/', null=True, blank=True, verbose_name="Profile Picture")
    institution_head_name = models.CharField(max_length=100, blank=True, verbose_name="Institution Head Name")
    website = models.URLField(blank=True, verbose_name="Website URL")
    description = models.TextField(blank=True, verbose_name="About the Institution")

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

class Tender(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
        ('expired', 'Expired'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='tenders')
    created_by = models.ForeignKey(InstitutionUser, on_delete=models.CASCADE, related_name='created_tenders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True, null=True, help_text="Reason for rejection, if applicable.")
    
    def __str__(self):
        return self.title

    def get_status_badge_class(self):
        return {
            'draft': 'bg-gray-100 text-gray-800',
            'pending_review': 'bg-orange-100 text-orange-800',
            'pending_approval': 'bg-yellow-100 text-yellow-800',
            'approved': 'bg-green-100 text-green-800',
            'published': 'bg-blue-100 text-blue-800',
            'rejected': 'bg-red-100 text-red-800',
            'archived': 'bg-purple-100 text-purple-800',
            'expired': 'bg-gray-100 text-gray-800 ring-1 ring-inset ring-gray-500/20',
        }.get(self.status, 'bg-gray-100 text-gray-800')

    def log_activity(self, user, action, remarks=None):
        """Helper method to create a log entry for this tender."""
        TenderActivity.objects.create(tender=self, performed_by=user, action=action, remarks=remarks)

class TenderActivity(models.Model):
    """Logs all significant actions performed on a tender."""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='activities')
    performed_by = models.ForeignKey(InstitutionUser, on_delete=models.SET_NULL, null=True, related_name='tender_activities')
    action = models.CharField(max_length=100) # e.g., "Created", "Submitted for Review", "Published"
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"'{self.action}' on '{self.tender.title}' at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"