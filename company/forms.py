from django import forms
from .models import Company
from django.contrib.auth.forms import PasswordChangeForm as AuthPasswordChangeForm

class CompanyProfileForm(forms.ModelForm):
    """Form for companies to update their profile."""
    class Meta:
        model = Company
        fields = ['company_name', 'email', 'phone_number', 'website', 'address', 'description', 'profile_picture']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
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

class CompanyVerificationForm(forms.ModelForm):
    """
    A form for companies to submit their verification documents.
    """
    class Meta:
        model = Company
        fields = [
            'company_name', 'email', 'phone_number', 'address', 'website',
            'registration_number', 'pan_number', 'registration_certificate'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'Your official company name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Official contact email'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Official contact number'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full official address'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://www.example.com'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'e.g., UXX-XXXX-XXXX'}),
            'pan_number': forms.TextInput(attrs={'placeholder': 'e.g., ABCDE1234F'}),
            'registration_certificate': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_fields = ['company_name', 'email', 'phone_number', 'address', 'registration_number', 'pan_number', 'registration_certificate']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True