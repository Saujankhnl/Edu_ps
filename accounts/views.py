from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from .forms import InstitutionRegistrationForm, CompanyRegistrationForm
from company.models import Company
from institution.models import Institution, InstitutionUser
from tenders.models import Tender

def home(request): # Renamed from homepage
    """Displays the main landing page with a list of recent tenders."""
    # Fetch recently published tenders to display on the homepage
    recent_tenders = Tender.objects.filter(status='published').order_by('-updated_at')[:6]
    
    context = {
        'tenders': recent_tenders,
    }
    return render(request, 'accounts/home.html', context)

def login_page(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if hasattr(user, 'institution_profile'):
                    return redirect('institution:dashboard')
                elif hasattr(user, 'company'):
                    return redirect('company:dashboard')
                else:
                    return redirect('accounts:home')
            else:
                messages.error(request,"Invalid username or password.")
        else:
            messages.error(request,"Invalid username or password.")
    form = AuthenticationForm()
    return render(request=request, template_name="accounts/login_page.html", context={"login_form":form})

def register_page(request): # Renamed from register
    """Handles the registration for both institutions and companies."""
    if request.method == 'POST':
        if 'register_institution' in request.POST:
            institution_form = InstitutionRegistrationForm(request.POST)
            if institution_form.is_valid():
                with transaction.atomic():
                    # Create the base Django User for the admin
                    admin_user = User.objects.create_user(
                        username=institution_form.cleaned_data['username'],
                        password=institution_form.cleaned_data['password'],
                        email=institution_form.cleaned_data['email']
                    )
                    # Create the Institution, linking it to the admin user
                    institution = institution_form.save(commit=False)
                    institution.user = admin_user
                    institution.save()
                    # Create the InstitutionUser profile for the admin
                    InstitutionUser.objects.create(user=admin_user, institution=institution, role='admin')

                messages.success(request, "Institution registration successful. Please log in.")
                return redirect('accounts:login_page')
            company_form = CompanyRegistrationForm(request.POST) # Repopulate with submitted data
        elif 'register_company' in request.POST:
            company_form = CompanyRegistrationForm(request.POST)
            if company_form.is_valid():
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=company_form.cleaned_data['username'],
                        password=company_form.cleaned_data['password'],
                        email=company_form.cleaned_data['email']
                    )
                    company = company_form.save(commit=False)
                    company.user = user
                    company.save()
                messages.success(request, "Company registration successful. Please log in.")
                return redirect('accounts:login_page')
            institution_form = InstitutionRegistrationForm(request.POST) # Repopulate with submitted data
        else: # Handle cases where the form submission is not recognized
            institution_form = InstitutionRegistrationForm(request.POST)
            company_form = CompanyRegistrationForm(request.POST)
    else:
        institution_form = InstitutionRegistrationForm()
        company_form = CompanyRegistrationForm()
        
    return render(request, 'accounts/register.html', {'institution_form': institution_form, 'company_form': company_form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('accounts:home')

def forget_password(request):
    # Placeholder view
    return render(request, 'accounts/forget_password.html')

def verify_otp(request):
    # Placeholder view
    return render(request, 'accounts/verify_otp.html')

def reset_password(request):
    # Placeholder view
    return render(request, 'accounts/reset_password.html')