from django.db import models
from django.contrib.auth.models import User
from institution.models import Tender

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

class Bid(models.Model):
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bids')
    bid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    proposal_document = models.FileField(upload_to='proposals/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    class Meta:
        # A company can only bid once on a specific tender
        unique_together = ('tender', 'company')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Bid by {self.company.company_name} on {self.tender.title}"
