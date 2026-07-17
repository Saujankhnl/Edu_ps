from django import forms
from django.contrib.auth.models import User
from institution.models import Institution
from company.models import Company

class InstitutionRegistrationForm(forms.ModelForm):
    """Form for registering a new Institution and its admin user."""
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Create a unique username', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create robust password', 'class': 'password-input w-full border border-gray-300 rounded-xl pl-4 pr-12 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'}), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'}), required=True, label="Confirm Password")

    class Meta:
        model = Institution
        fields = ['institution_name', 'email', 'phone_number', 'address']
        widgets = {
            'institution_name': forms.TextInput(attrs={'placeholder': 'e.g., EduPs Academy', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'}),
            'email': forms.EmailInput(attrs={'placeholder': 'admin@institution.com', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Enter phone number', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full legal location address', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition resize-none'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data

class CompanyRegistrationForm(forms.ModelForm):
    """Form for registering a new Company and its user."""
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Create a unique username', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create robust password', 'class': 'password-input w-full border border-gray-300 rounded-xl pl-4 pr-12 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition'}), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition'}), required=True, label="Confirm Password")

    class Meta:
        model = Company
        fields = ['company_name', 'email', 'phone_number', 'address']
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g., EduPs Logistics Ltd', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition'}),
            'email': forms.EmailInput(attrs={'placeholder': 'contact@company.com', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Enter phone number', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Corporate office address', 'class': 'w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition resize-none'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data