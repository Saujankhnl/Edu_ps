from django import forms
from .models import Tender, Bid
from decimal import Decimal

from django.utils import timezone
class TenderForm(forms.ModelForm):
    """Form for creating and editing a tender."""
    class Meta:
        model = Tender
        fields = ['title', 'category', 'description', 'budget', 'deadline', 'opening_date', 'terms_and_conditions', 'eligibility_criteria', 'technical_requirements', 'tender_document']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'eligibility_criteria': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'technical_requirements': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'tender_document': forms.FileInput(attrs={'class': 'form-input'}),
            'budget': forms.NumberInput(attrs={
                'class': 'form-input w-full text-sm rounded-xl pl-8 pr-4 py-2.5 border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all bg-gray-50/50 focus:bg-white',
                'placeholder': 'e.g., 50000.00',
                'step': '0.01',
                'min': '0'
            }),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'opening_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        self.fields['opening_date'].widget.attrs['min'] = now_str
        self.fields['deadline'].widget.attrs['min'] = now_str

    def clean_budget(self):
        """
        Custom validation to ensure the budget, if provided, is at least 1,000,000.
        """
        budget = self.cleaned_data.get('budget')
        min_budget = Decimal('1000000.00')
        if budget is not None and budget < min_budget:
            raise forms.ValidationError(f"The budget must be at least Np {min_budget:,.2f}.")
        return budget

    def clean_opening_date(self):
        # Add a 1-minute grace period to prevent race condition errors.
        # This allows submissions for the current minute to be valid.
        now_with_grace = timezone.now() - timezone.timedelta(minutes=1)
        opening_date = self.cleaned_data.get('opening_date')
        
        if opening_date and opening_date < now_with_grace:
            raise forms.ValidationError("The bidding opening date cannot be in the past.")
        return opening_date

    def clean_deadline(self):
        # Add a 1-minute grace period here as well for consistency.
        now_with_grace = timezone.now() - timezone.timedelta(minutes=1)
        deadline = self.cleaned_data.get('deadline')

        if deadline and deadline < now_with_grace:
            raise forms.ValidationError("The submission deadline cannot be in the past.")
        return deadline

    def clean(self):
        cleaned_data = super().clean()
        opening_date = cleaned_data.get("opening_date")
        deadline = cleaned_data.get("deadline")

        if opening_date and deadline and deadline <= opening_date:
            self.add_error('deadline', "The submission deadline must be after the bidding opening date.")
        return cleaned_data

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