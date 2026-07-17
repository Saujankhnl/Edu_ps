from django.db import models
from django.contrib.auth.models import User

class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    website = models.URLField(blank=True, verbose_name="Website URL")
    description = models.TextField(blank=True, verbose_name="About the Company")
    profile_picture = models.ImageField(upload_to='company_logos/', null=True, blank=True, verbose_name="Company Logo")

    def __str__(self):
        return self.company_name
