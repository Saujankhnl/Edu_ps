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