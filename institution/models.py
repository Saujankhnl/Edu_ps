from django.db import models
from django.contrib.auth.models import User

class Institution(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_admin_profile')
    institution_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()

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
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='tenders')
    created_by = models.ForeignKey(InstitutionUser, on_delete=models.CASCADE, related_name='created_tenders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        }.get(self.status, 'bg-gray-100 text-gray-800')