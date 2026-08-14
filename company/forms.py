from django import forms
import re
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
            'registration_number': forms.TextInput(attrs={
                'placeholder': '5-20 characters (A-Z, 0-9, /,-)',
                'pattern': r'[A-Za-z0-9\/-]{5,20}',
                'title': 'Must be 5-20 characters and can only contain letters, numbers, hyphens (-), and slashes (/).',
                'minlength': '5', 'maxlength': '20'
            }),
            'pan_number': forms.TextInput(attrs={'placeholder': 'Enter 9-digit PAN number', 'pattern': r'\d{9}', 'title': 'PAN number must be 9 digits.'}),
            'registration_certificate': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_fields = ['company_name', 'email', 'phone_number', 'address', 'registration_number', 'pan_number', 'registration_certificate']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def clean_pan_number(self):
        pan_number = self.cleaned_data.get('pan_number')
        if pan_number and (not pan_number.isdigit() or len(pan_number) != 9):
            raise forms.ValidationError("PAN number must be exactly 9 digits and contain only numbers.")
        return pan_number

    def clean_registration_certificate(self):
        file = self.cleaned_data.get('registration_certificate', False)
        if file:
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError("File size cannot exceed 10MB.")
        return file

    def clean_pan_number(self):
        pan_number = self.cleaned_data.get('pan_number')
        if pan_number and (not pan_number.isdigit() or len(pan_number) != 9):
            raise forms.ValidationError("PAN number must be exactly 9 digits and contain only numbers.")
        return pan_number

    def clean_registration_number(self):
        reg_number = self.cleaned_data.get('registration_number')
        if reg_number:
            if not (5 <= len(reg_number) <= 20):
                raise forms.ValidationError("Registration number must be between 5 and 20 characters long.")
            if not re.match(r'^[A-Za-z0-9\/-]+$', reg_number):
                raise forms.ValidationError("Registration number can only contain letters, numbers, hyphens (-), and slashes (/).")
        return reg_number
class CompanyUserCreationForm(forms.Form):
    """Form for a Company Admin to create new users for their company."""
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    role = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Admin can only create Bid Submitters or Viewers.
        self.fields['role'].choices = [
            (role, display) for role, display in Company.ROLE_CHOICES if role in ['bid_submitter', 'viewer']
        ]

class CompanyUserChangeForm(forms.ModelForm):
    """Form for a Company Admin to edit existing users."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = Company
        fields = ['email', 'first_name', 'last_name', 'role']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Admin can only assign Bid Submitter or Viewer roles.
        self.fields['role'].choices = [
            (role, display) for role, display in Company.ROLE_CHOICES if role in ['bid_submitter', 'viewer']
        ]

class CompanyUserProfileForm(forms.ModelForm):
    """Form for a company user to edit their own profile details."""
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Company
        # This form edits fields on both User and Company models.
        # We list the Company model fields here.
        # The view will handle updating the User model separately.
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-input'}),
        }