from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.db import transaction

from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from io import BytesIO
from xhtml2pdf import pisa

from .decorators import company_login_required, company_role_required
from .models import Company
from tenders.models import Tender, Bid
from .forms import CompanyProfileForm, PasswordChangeForm, CompanyVerificationForm, CompanyUserCreationForm, CompanyUserChangeForm, CompanyUserProfileForm

@company_login_required
def dashboard(request):
    company = get_object_or_404(Company, user=request.user)

    # --- Verification Flow Enforcement ---
    # Always re-fetch the company object to get the latest status.
    company = get_object_or_404(Company, pk=company.pk)

    if company.verification_status == 'pending':
        return render(request, 'company/verification_pending.html', {'company': company})
    elif company.verification_status != 'approved': # Handles 'not_submitted' and 'rejected'
        messages.info(request, "Please complete your company profile and submit for verification to access all features.")
        return redirect('company:verification')
    
    # Stats
    total_published_tenders = Tender.objects.filter(status='published').count()
    
    # For all company roles (admin, viewer, etc.), we should get stats for the entire company.
    # We can find the admin of the company to get the "main" company entity if needed,
    # but a better approach is to filter Bids by the company_name.
    # Assuming all users of a company share the same `company_name`.
    my_bids = Bid.objects.filter(company__company_name=company.company_name)
    
    stats = {
        'total_published_tenders': total_published_tenders,
        'total_submitted_bids': my_bids.count(),
        'active_bids': my_bids.filter(status__in=['submitted', 'under_review', 'shortlisted']).count(),
        'successful_bids': my_bids.filter(status='accepted').count(),
        'rejected_bids': my_bids.filter(status='rejected').count(),
        # The 'total_failed_offers' key is used in analytics_reports.html, let's keep it consistent.
        'total_failed_offers': my_bids.filter(status='rejected').count(),
    }

    # Recent activities (e.g., recent bids)
    recent_activities = my_bids.select_related('tender').order_by('-submitted_at')[:5]

    # Bids pending company admin approval.
    # We filter for `remarks__isnull=True` because a bid with remarks has already been rejected by the admin.
    pending_admin_approval_bids = Bid.objects.filter(
        company__company_name=company.company_name, status='pending_approval', remarks__isnull=True
    )

    context = {
        'company': company,
        'stats': stats,
        'recent_activities': recent_activities,
        'role': company.role,
        'pending_admin_approval_bids': pending_admin_approval_bids,
    }
    return render(request, 'company/company_dashboard.html', context)

@company_login_required
@company_role_required(allowed_roles=['admin'])
def company_profile(request):
    # Get the current user's company profile to know their role and company name
    current_user_company_profile = get_object_or_404(Company, user=request.user)
    
    # The "main" profile is the one associated with the 'admin' role for that company name.
    # We fetch this to display consistent company-wide information for all users of the company.
    main_company_profile = Company.objects.filter(
        company_name=current_user_company_profile.company_name, 
        role='admin'
    ).first()

    if not main_company_profile:
        # Fallback to the user's own profile if an admin profile isn't found for some reason.
        main_company_profile = current_user_company_profile

    # Pass the main profile for display, but the current user's role for permissions.
    context = {'company': main_company_profile, 'role': current_user_company_profile.role}
    return render(request, 'company/company_profile.html', context)

@company_login_required
def user_profile(request):
    """Displays the logged-in company user's own profile details."""
    profile = get_object_or_404(Company, user=request.user)
    return render(request, 'company/user_profile.html', {'profile': profile})

@company_login_required
def edit_user_profile(request):
    """Allows a company user to edit their own profile details."""
    profile = get_object_or_404(Company, user=request.user)
    user = request.user

    if request.method == 'POST':
        form = CompanyUserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            with transaction.atomic():
                # Save Company model fields from the form
                profile_instance = form.save(commit=False)
                
                # Manually update User model fields from the form's cleaned_data
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                
                user.save()
                profile_instance.save()

            messages.success(request, "Your profile has been updated successfully.")
            return redirect('company:user_profile')
    else:
        # Pre-populate the form with data from both models
        initial_data = {'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email}
        form = CompanyUserProfileForm(instance=profile, initial=initial_data)

    return render(request, 'company/edit_user_profile.html', {'form': form, 'profile': profile})

@company_login_required
@company_role_required(allowed_roles=['admin'])
def edit_company_profile(request):
    company = get_object_or_404(Company, user=request.user)
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('company:company_profile')
    else:
        form = CompanyProfileForm(instance=company)
    return render(request, 'company/edit_company_profile.html', {'form': form, 'company': company, 'role': company.role})

@company_login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('company:dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'company/change_password.html', {'form': form, 'company': request.user.company, 'role': request.user.company.role})

@company_login_required
@company_role_required(allowed_roles=['admin', 'bid_submitter'])
def list_published_tenders(request):
    search_query = request.GET.get('q', '')
    tenders = Tender.objects.filter(status='published').order_by('-updated_at')

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
    return render(request, 'company/list_tenders.html', context)

@company_login_required
@company_role_required(allowed_roles=['admin', 'viewer'])
def analytics_reports(request):
    company = get_object_or_404(Company, user=request.user)
    my_bids = Bid.objects.filter(company=company)

    total_bids = my_bids.count() # Total bids submitted
    successful_bids = my_bids.filter(status='accepted').count() # Bids accepted by institution
    pending_bids = my_bids.filter(status__in=['submitted', 'under_review', 'shortlisted']).count() # Bids awaiting decision
    total_failed_offers = my_bids.filter(status='rejected').count() # Only rejected bids count as failed

    context = {
        'total_bids': total_bids,
        'successful_bids': successful_bids,
        'pending_bids': pending_bids,
        'total_failed_offers': total_failed_offers,
        'company': company,
        'role': company.role,
    }
    return render(request, 'company/analytics_reports.html', context)

def render_to_pdf(template_src, context_dict={}):
    """Helper function to render a Django template to a PDF."""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('We had some errors<pre>%s</pre>' % html, status=500)

@company_login_required
@company_role_required(allowed_roles=['admin'])
def generate_analytics_pdf(request):
    """Generates a PDF report of the company's bidding analytics."""
    company = get_object_or_404(Company, user=request.user)
    my_bids = Bid.objects.filter(company=company)

    # Fetch the same stats as the analytics page
    total_bids = my_bids.count()
    successful_bids = my_bids.filter(status='accepted').count()
    pending_bids = my_bids.filter(status__in=['submitted', 'under_review', 'shortlisted']).count()
    rejected_bids = my_bids.filter(status='rejected').count()

    context = {
        'company': company,
        'total_bids': total_bids,
        'successful_bids': successful_bids,
        'pending_bids': pending_bids,
        'rejected_bids': rejected_bids,
        'report_date': timezone.now(),
        'all_bids': my_bids.select_related('tender').order_by('-submitted_at'),
    }

    pdf = render_to_pdf('company/report_pdf_template.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Bidding_Analytics_Report_{company.company_name.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    messages.error(request, "There was an error generating the PDF report.")
    return redirect('company:analytics_reports')

@company_login_required
def verification_submission(request):
    """
    Allows a company user to submit or update their verification documents.
    """
    company = get_object_or_404(Company, user=request.user)

    if company.verification_status == 'approved':
        messages.success(request, "Your company is already verified.")
        return redirect('company:dashboard')

    if request.method == 'POST':
        form = CompanyVerificationForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            instance = form.save(commit=False)
            if instance.verification_status in ['not_submitted', 'rejected']:
                instance.verification_status = 'pending'
                instance.verification_remarks = "" # Clear old remarks
            instance.save()
            messages.success(request, "Your verification documents have been submitted and are pending review.")
            return redirect('company:verification')
    else:
        form = CompanyVerificationForm(instance=company)

    context = {'form': form, 'company': company}
    return render(request, 'company/verification_form.html', context)

@company_login_required
@company_role_required(allowed_roles=['admin'])
def manage_users(request):
    """Allows a Company Admin to view and manage their users."""
    admin_company = get_object_or_404(Company, user=request.user, role='admin')
    
    # Get all users belonging to the same company, excluding the admin themselves.
    # This is a bit tricky because there isn't a direct link between company users.
    # We assume users are linked by being part of the same conceptual "company",
    # but the model has a User 1-to-1 with Company.
    # For this implementation, we'll assume an admin manages users they create.
    # A better model would be a ManyToMany from Company to User through a membership model.
    # Given the current structure, an admin can only manage their own account details.
    # To enable user management, the data model needs to change from OneToOne to ForeignKey
    # from Company to User, and Company needs to be a single entity.
    
    # Let's adjust the logic based on the request. The request implies multiple users per company.
    # This means the `user` field on `Company` should be a `ForeignKey` not `OneToOneField`.
    # I will proceed assuming this change is made.
    
    # Let's find the parent company entity. Assuming the admin's `company_name` is the key.
    users_in_company = Company.objects.filter(company_name=admin_company.company_name).select_related('user').order_by('user__first_name')

    context = {
        'company': admin_company,
        'role': admin_company.role,
        'users': users_in_company,
    }
    return render(request, 'company/manage_users.html', context)

@company_login_required
@company_role_required(allowed_roles=['admin'])
def create_company_user(request):
    """View for a Company Admin to create a new user."""
    admin_company = get_object_or_404(Company, user=request.user, role='admin')
    if request.method == 'POST':
        form = CompanyUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    new_user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', '')
                    )
                    # Create a new Company profile for this user, inheriting details from the admin's company
                    Company.objects.create(
                        user=new_user,
                        role=form.cleaned_data['role'],
                        email=form.cleaned_data['email'],
                        company_name=admin_company.company_name,
                        # Copy other relevant details if necessary
                        verification_status=admin_company.verification_status,
                        is_approved=admin_company.is_approved,
                    )
                messages.success(request, f"User '{new_user.username}' created successfully.")
                return redirect('company:manage_users')
            except IntegrityError:
                form.add_error('username', 'A user with this username or email already exists.')
    else:
        form = CompanyUserCreationForm()

    context = {
        'form': form,
        'company': admin_company,
        'role': admin_company.role,
    }
    # This view requires a 'create_user.html' template in the company/templates/company/ directory.
    # Assuming one will be created, similar to the institution app.
    return render(request, 'company/create_user.html', context)

@company_login_required
@company_role_required(allowed_roles=['admin'])
def edit_company_user(request, user_id):
    """View for a Company Admin to edit an existing user."""
    admin_company = get_object_or_404(Company, user=request.user, role='admin')
    user_to_edit = get_object_or_404(User, pk=user_id)
    profile_to_edit = get_object_or_404(Company, user=user_to_edit)

    # Security Check: Ensure the user being edited belongs to the same company and is not an admin.
    if profile_to_edit.company_name != admin_company.company_name or profile_to_edit.role == 'admin':
        messages.error(request, "You do not have permission to edit this user.")
        return redirect('company:manage_users')

    if request.method == 'POST':
        form = CompanyUserChangeForm(request.POST, instance=profile_to_edit)
        if form.is_valid():
            with transaction.atomic():
                # Update the Company profile (role)
                profile = form.save(commit=False)
                # Update the base User model fields
                user_to_edit.first_name = form.cleaned_data['first_name']
                user_to_edit.last_name = form.cleaned_data['last_name']
                user_to_edit.email = form.cleaned_data['email']
                user_to_edit.save()
                profile.save()
            messages.success(request, f"User '{user_to_edit.username}' updated successfully.")
            return redirect('company:manage_users')
    else:
        initial_data = {'first_name': user_to_edit.first_name, 'last_name': user_to_edit.last_name, 'email': user_to_edit.email}
        form = CompanyUserChangeForm(instance=profile_to_edit, initial=initial_data)

    context = {
        'form': form,
        'user_to_edit': user_to_edit,
        'company': admin_company,
        'role': admin_company.role,
    }
    return render(request, 'company/edit_user.html', context)

@company_login_required
@company_role_required(allowed_roles=['admin'])
def delete_company_user(request, user_id):
    """View for a Company Admin to delete a user."""
    admin_company = get_object_or_404(Company, user=request.user, role='admin')
    user_to_delete = get_object_or_404(User, pk=user_id)
    profile_to_delete = get_object_or_404(Company, user=user_to_delete)

    if profile_to_delete.company_name != admin_company.company_name or profile_to_delete.role == 'admin':
        messages.error(request, "You do not have permission to delete this user.")
        return redirect('company:manage_users')

    if request.method == 'POST':
        username = user_to_delete.username
        user_to_delete.delete() # This will cascade and delete the Company profile due to OneToOneField
        messages.success(request, f"User '{username}' has been deleted.")
        return redirect('company:manage_users')

    context = {
        'user_to_delete': user_to_delete,
        'company': admin_company,
        'role': admin_company.role,
    }
    return render(request, 'company/delete_user_confirm.html', context)

# NOTE: Full implementation of create/edit/delete users for a company requires a significant
# data model change (from OneToOne to ForeignKey/ManyToMany). The provided code is a conceptual
# placeholder. The user management feature as requested is not fully possible without altering the
# core `Company` model relationship to `User`. The rest of the role implementation is valid.