from django import forms
from .models import Tender, Bid

class TenderForm(forms.ModelForm):
    """Form for creating and editing a tender."""
    class Meta:
        model = Tender
        fields = ['title', 'description', 'budget', 'deadline', 'terms_and_conditions', 'eligibility_criteria', 'technical_requirements', 'tender_document']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'eligibility_criteria': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'technical_requirements': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'tender_document': forms.FileInput(attrs={'class': 'form-input'}),
            'budget': forms.NumberInput(attrs={
                'class': 'form-input w-full text-sm rounded-xl pl-8 pr-4 py-2.5 border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all bg-gray-50/50 focus:bg-white',
                'placeholder': 'e.g., 50000.00',
                'step': '0.01',
                'min': '0'
            }),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        }

class BidSubmissionForm(forms.ModelForm):
    """Form for a company to submit a bid for a tender."""
    terms_agreement = forms.BooleanField(
        required=True,
        label="I have read and agree to the Terms & Conditions of this tender.",
        widget=forms.CheckboxInput() # The template will handle the styling
    )

    class Meta:
        model = Bid
        fields = ['bid_amount', 'proposal_document', 'quotation_document', 'cover_letter']
        widgets = {
            'bid_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'e.g., 45000.00'}),
            'proposal_document': forms.FileInput(attrs={'class': 'form-input'}),
            'quotation_document': forms.FileInput(attrs={'class': 'form-input'}),
            'cover_letter': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Optional: Add any remarks or a cover letter here...'}),
        }