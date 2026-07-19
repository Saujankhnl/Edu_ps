from django import forms
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.models import User

# Assuming EmailForm and OTPForm are also defined in accounts/forms.py
# These are included for completeness as they are imported by accounts/views.py
class EmailForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com'})
    )

class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '------'})
    )

# This is the crucial form for the password reset logic
class SetPasswordForm(DjangoSetPasswordForm):
    """
    A custom SetPasswordForm to apply Tailwind CSS classes and ensure correct
    inheritance from Django's built-in SetPasswordForm for password saving logic.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'password-input w-full border border-gray-200 rounded-xl pl-4 pr-12 py-3.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder-transparent',
            'placeholder': ' ' # Placeholder for floating label effect
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'password-input w-full border border-gray-200 rounded-xl pl-4 pr-12 py-3.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder-transparent',
            'placeholder': ' ' # Placeholder for floating label effect
        })

# Note: InstitutionRegistrationForm and CompanyRegistrationForm would also need
# to be defined in this file if they are not in separate files, as they are
# imported by accounts/views.py. Their definitions are not included here as
# they are not directly relevant to the password reset functionality.