from django import forms
from .models import Company, Bid
from django.contrib.auth.forms import PasswordChangeForm as AuthPasswordChangeForm

class CompanyProfileForm(forms.ModelForm):
    """Form for companies to update their profile."""
    class Meta:
        model = Company
        fields = ['phone_number', 'website', 'address', 'description', 'profile_picture']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-input'}),
            'website': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://www.example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }

class PasswordChangeForm(AuthPasswordChangeForm):
    """Custom password change form to apply Tailwind CSS classes."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget = forms.PasswordInput(attrs={
            'class': 'form-input', 'placeholder': 'Enter your current password'
        })
        self.fields['new_password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-input', 'placeholder': 'Enter new password'
        })
        self.fields['new_password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-input', 'placeholder': 'Confirm new password'
        })

class BidSubmissionForm(forms.ModelForm):
    """Form for submitting a bid on a tender."""
    class Meta:
        model = Bid
        fields = ['bid_amount', 'proposal_document']
        widgets = {
            'bid_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Enter your bid amount'}),
            'proposal_document': forms.FileInput(attrs={'class': 'form-input'}),
        }