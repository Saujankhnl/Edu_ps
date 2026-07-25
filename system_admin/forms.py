from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm as AuthPasswordChangeForm

class AdminProfileForm(forms.ModelForm):
    """Form for the System Admin to update their own profile details."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }
        help_texts = {
            'username': 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

class AdminPasswordChangeForm(AuthPasswordChangeForm):
    """Custom password change form to apply consistent styling."""
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