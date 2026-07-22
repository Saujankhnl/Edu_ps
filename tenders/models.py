from django.db import models
from django.conf import settings
from institution.models import Institution, InstitutionUser

class Tender(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('pending_approval', 'Pending Approval'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='tenders')
    created_by = models.ForeignKey(InstitutionUser, on_delete=models.SET_NULL, null=True, related_name='created_tenders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    eligibility_criteria = models.TextField(blank=True, null=True)
    technical_requirements = models.TextField(blank=True, null=True)
    tender_document = models.FileField(upload_to='PDF/tender_documents/', null=True, blank=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.title

    def get_status_badge_class(self):
        return {
            'draft': 'bg-gray-100 text-gray-800',
            'pending_review': 'bg-yellow-100 text-yellow-800',
            'pending_approval': 'bg-blue-100 text-blue-800',
            'published': 'bg-green-100 text-green-800',
            'rejected': 'bg-red-100 text-red-800',
            'completed': 'bg-purple-100 text-purple-800',
            'expired': 'bg-gray-100 text-gray-800',
        }.get(self.status, 'bg-gray-100 text-gray-800')

    def return_to_creator(self, reviewer, remarks_text):
        """
        Handles the business logic for a reviewer returning a tender to the creator.
        
        Args:
            reviewer (InstitutionUser): The reviewer performing the action.
            remarks_text (str): The mandatory remarks for the creator.
        """
        self.status = 'rejected'
        self.remarks = remarks_text
        self.log_activity(reviewer, "Returned to Creator", remarks=remarks_text)

    def reject_by_admin(self, admin_user, remarks_text):
        """
        Handles the business logic for an admin rejecting a tender.

        Args:
            admin_user (InstitutionUser): The admin performing the action.
            remarks_text (str): The mandatory remarks for the rejection.
        """
        self.status = 'rejected'
        self.remarks = remarks_text
        self.log_activity(admin_user, "Rejected", remarks=remarks_text)

    def log_activity(self, user, action, remarks=None):
        """Logs an activity related to this tender."""
        TenderActivity.objects.create(
            tender=self,
            performed_by=user,
            action=action,
            remarks=remarks
        )

class TenderActivity(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='activities')
    performed_by = models.ForeignKey(InstitutionUser, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

class Bid(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids')
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='bids')
    bid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    proposal_document = models.FileField(upload_to='PDF/proposal/', null=True, blank=True)
    quotation_document = models.FileField(upload_to='PDF/quotation/', null=True, blank=True)
    cover_letter = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    def __str__(self):
        return f"Bid by {self.company.company_name} for {self.tender.title}"