from django import forms
from django.contrib.auth.models import User
import re
from .models import Institution, InstitutionUser
from django.contrib.auth.forms import PasswordChangeForm as AuthPasswordChangeForm

class InstitutionUserCreationForm(forms.ModelForm):
    """
    A form for creating new users (Creators/Reviewers) by an Institution Admin.
    """
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=True)
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = InstitutionUser
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Admin can only create Creators or Reviewers, not other Admins.
        self.fields['role'].choices = [
            (role, display) for role, display in InstitutionUser.ROLE_CHOICES if role in ['creator', 'reviewer']
        ]

class InstitutionUserChangeForm(forms.ModelForm):
    """
    A form for updating existing users by an Institution Admin.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = InstitutionUser
        fields = ['email', 'first_name', 'last_name', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            (role, display) for role, display in InstitutionUser.ROLE_CHOICES if role in ['creator', 'reviewer']
        ]

class InstitutionProfileForm(forms.ModelForm):
    """Form for an admin to update their institution's public profile."""
    class Meta:
        model = Institution
        fields = ['institution_name', 'email', 'phone_number', 'website', 'institution_head_name', 'address', 'description', 'profile_picture']
        widgets = {
            'institution_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input'}),
            'website': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://www.example.com'}),
            'institution_head_name': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }

class UserProfileForm(forms.ModelForm):
    """Form for users to update their own profile information."""
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = InstitutionUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': 'Your contact number'}),
            'profile_picture': forms.ClearableFileInput(),
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

class InstitutionVerificationForm(forms.ModelForm):
    """
    A form for institutions to submit their verification documents.
    """
    class Meta:
        model = Institution
        fields = [
            'institution_name', 'institution_type', 'email', 'phone_number', 'address', 'website',
            'contact_person', 'contact_person_number',
            'registration_number', 'pan_number',
            'registration_certificate', 'pan_certificate', 'authorization_letter', 'profile_picture'
        ]
        widgets = {
            'institution_name': forms.TextInput(attrs={'placeholder': 'Your official institution name'}),
            'institution_type': forms.Select(),
            'email': forms.EmailInput(attrs={'placeholder': 'Official contact email'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Official contact number'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full official address'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://www.example.edu'}),
            'contact_person': forms.TextInput(attrs={'placeholder': 'Full name of the primary contact'}),
            'contact_person_number': forms.TextInput(attrs={'placeholder': 'Mobile or direct line of the contact person'}),
            'registration_number': forms.TextInput(attrs={
                'placeholder': '5-20 characters (A-Z, 0-9, /,-)',
                'pattern': r'[A-Za-z0-9\/-]{5,20}',
                'title': 'Must be 5-20 characters and can only contain letters, numbers, hyphens (-), and slashes (/).',
                'minlength': '5', 'maxlength': '20'
            }),
            'pan_number': forms.TextInput(attrs={'placeholder': 'Enter 9-digit PAN number', 'pattern': r'\d{9}', 'title': 'PAN number must be 9 digits.'}),
            'registration_certificate': forms.ClearableFileInput(),
            'pan_certificate': forms.ClearableFileInput(),
            'authorization_letter': forms.ClearableFileInput(),
            'profile_picture': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set required fields dynamically
        required_fields = ['institution_name', 'email', 'phone_number', 'address', 'contact_person', 'contact_person_number', 'registration_number', 'pan_number', 'registration_certificate']
        for field_name in required_fields:
            self.fields[field_name].required = True

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