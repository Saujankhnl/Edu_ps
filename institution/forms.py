from django import forms
from django.contrib.auth.models import User
from .models import Institution, InstitutionUser, Tender
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

class TenderForm(forms.ModelForm):
    """Form for creating and editing a tender."""
    class Meta:
        model = Tender
        fields = ['title', 'description', 'deadline']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
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