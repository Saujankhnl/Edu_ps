import random
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from .forms import InstitutionRegistrationForm, CompanyRegistrationForm, EmailForm, OTPForm, SetPasswordForm
from company.models import Company
from institution.models import Institution, InstitutionUser
from django.db.models import Q
from django.utils import timezone
from tenders.models import Tender

def home(request): # Renamed from homepage
    """Displays the main landing page with a list of recent tenders."""
    search_query = request.GET.get('q', '')
    now = timezone.now()

    # Fetch all publicly visible tenders that are still active.
    # This includes published tenders with a future deadline or no deadline.
    tenders = Tender.objects.filter(
        Q(status='published') & (Q(deadline__isnull=True) | Q(deadline__gt=now))
    ).select_related('institution').order_by('-updated_at')

    if search_query:
        tenders = tenders.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(institution__institution_name__icontains=search_query)
        )

    context = {
        'tenders': tenders,
        'search_query': search_query,
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
    """
    Handles the request for initiating password reset.
    Collects user's email, generates an OTP, stores it in the session,
    and prints it to the terminal.
    """
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate a random 6-digit OTP
                otp = str(random.randint(100000, 999999))
                
                # Store OTP, user's email, and user ID in the session
                request.session['reset_email'] = email
                request.session['otp'] = otp
                request.session['reset_user_id'] = user.id # Store user ID for later use

                # Print OTP to terminal as requested
                print("--------------------------------")
                print(f"--- Password Reset OTP for {email}: {otp} ---")
                print("--------------------------------")
                messages.success(request, "An OTP has been sent to your email (check terminal for now).")
                return redirect('accounts:verify_otp')
            except User.DoesNotExist:
                messages.error(request, "No user found with that email address.")
        else:
            messages.error(request, "Please enter a valid email address.")
    else:
        form = EmailForm()
    return render(request, 'accounts/forget_password.html', {'form': form})

def verify_otp(request):
    """
    Verifies the OTP entered by the user.
    If correct, allows the user to proceed to password reset.
    """
    # Ensure an OTP process has been initiated
    if 'reset_email' not in request.session or 'otp' not in request.session or 'reset_user_id' not in request.session:
        messages.error(request, "Please initiate the password reset process first.")
        return redirect('accounts:forget_password')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            stored_otp = request.session.get('otp')

            if entered_otp == stored_otp:
                # OTP is correct, clear OTP from session and proceed to reset password
                del request.session['otp']
                messages.success(request, "OTP verified successfully. You can now reset your password.")
                return redirect('accounts:reset_password')
            else:
                messages.error(request, "Wrong OTP. Please try again.")
        else:
            messages.error(request, "Please enter a valid 6-digit OTP.")
    else:
        form = OTPForm()
    
    context = {
        'form': form,
        'email': request.session.get('reset_email') # Display the email to the user
    }
    return render(request, 'accounts/verify_otp.html', context)

def reset_password(request):
    """
    Allows the user to set a new password after successful OTP verification.
    """
    # Ensure OTP has been verified and user ID is in session
    if 'reset_user_id' not in request.session:
        messages.error(request, "Please verify OTP before resetting your password.")
        return redirect('accounts:forget_password')

    # Retrieve the user object using the ID stored in the session
    user = User.objects.get(pk=request.session['reset_user_id'])

    if request.method == 'POST':
        form = SetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save() # This handles setting the new password and hashing it
            
            # Clear all session data related to password reset
            del request.session['reset_user_id']
            if 'reset_email' in request.session:
                del request.session['reset_email']

            messages.success(request, "Your password has been reset successfully. Please log in with your new password.")
            return redirect('accounts:login_page')
        else:
            # Form is invalid, errors will be displayed by the template
            # No need for an explicit messages.error here, as form.errors will handle it.
            pass
    else:
        form = SetPasswordForm(user=user)
    
    return render(request, 'accounts/reset_password.html', {'form': form})
