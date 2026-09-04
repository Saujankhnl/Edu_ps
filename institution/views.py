from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from .models import Institution, InstitutionUser
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When
from django.http import HttpResponseForbidden, Http404
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.template.loader import get_template
from io import BytesIO # Keep this import, it's used by render_to_pdf
from xhtml2pdf import pisa
from django.contrib import messages
from tenders.models import Tender, TenderActivity, Bid
from .decorators import role_required
from .forms import InstitutionUserCreationForm, InstitutionUserChangeForm, InstitutionProfileForm, UserProfileForm, PasswordChangeForm, InstitutionVerificationForm
from django.utils import timezone


@login_required
def dashboard(request):
    try:
        # Use select_related to fetch related Institution and User in one query for efficiency.
        institution_user = InstitutionUser.objects.select_related('institution', 'user').get(user=request.user)
        institution = institution_user.institution
        role = institution_user.role
    except InstitutionUser.DoesNotExist:
        # This can happen if a user exists but their InstitutionUser profile was deleted.
        # It's a fallback to prevent a crash.
        return render(request, 'institution/error_no_profile.html')

    # --- Verification Flow Enforcement ---
    if role == 'admin':
        # Always re-fetch the institution object right before the check to get the latest status.
        # This prevents showing a stale 'pending' page after an admin has approved the verification.
        institution = get_object_or_404(Institution, pk=institution.pk)

        if institution.verification_status == 'pending':
            return render(request, 'institution/verification_pending.html', {'institution': institution})
        elif institution.verification_status != 'approved': # Handles 'not_submitted' and 'rejected'
            return redirect('institution:verification')

    # Base querysets
    all_tenders_in_institution = Tender.objects.filter(institution=institution)
    
    # Auto-expire tenders
    expired_tenders = all_tenders_in_institution.filter(status='published', deadline__lt=timezone.now())
    if expired_tenders.exists():
        # Log this action for the first expired tender as a sample
        sample_tender = expired_tenders.first()
        if sample_tender:
            expired_count = expired_tenders.update(status='expired')
            sample_tender.log_activity(None, f"{expired_count} tender(s) auto-expired")

    # Prepare context
    context = {
        'institution_user': institution_user,
        'role': role,
        'stats': {},
        'tenders': [],
        'chart_data': {},
        'recent_activities': TenderActivity.objects.filter(tender__institution=institution).select_related('performed_by__user', 'tender').order_by('-timestamp')[:5]
    }

    if role == 'admin':
        stats = all_tenders_in_institution.aggregate(
            total_tenders=Count('id'),
            pending_approval=Count('id', filter=Q(status='pending_approval')),
            published=Count('id', filter=Q(status='published')),
            rejected=Count('id', filter=Q(status='rejected')),
            completed=Count('id', filter=Q(status='completed')),
            expired=Count('id', filter=Q(status='expired')),
        )
        stats['total_users'] = InstitutionUser.objects.filter(institution=institution).count()
        stats['total_bids'] = Bid.objects.filter(tender__institution=institution).count()

        context['stats'] = stats
        context['chart_data'] = {
            'labels': ['Published', 'Pending Approval', 'Completed', 'Rejected', 'Expired'],
            'data': [stats['published'], stats['pending_approval'], stats['completed'], stats['rejected'], stats['expired']],
        }
        # Show all non-draft/archived tenders on the admin dashboard for a complete overview.
        context['tenders'] = all_tenders_in_institution.exclude(status='draft').order_by('-updated_at')

    elif role == 'creator':
        creator_tenders = all_tenders_in_institution.filter(created_by=institution_user)
        stats = creator_tenders.aggregate(
            total=Count('id'),
            draft=Count('id', filter=Q(status='draft')),
            pending_review=Count('id', filter=Q(status='pending_review')),
            rejected=Count('id', filter=Q(status='rejected')),
            published=Count('id', filter=Q(status='published')),
        )
        context['stats'] = stats
        context['chart_data'] = {
            'labels': ['Draft', 'Pending Review', 'Published', 'Rejected'],
            'data': [stats['draft'], stats['pending_review'], stats['published'], stats['rejected']],
        }
        context['tenders'] = creator_tenders.order_by('-updated_at')

    elif role == 'reviewer':
        # Correctly calculate stats for reviewers
        reviewer_activities = TenderActivity.objects.filter(
            performed_by=institution_user, 
            action__in=["Forwarded for Approval", "Returned to Creator"]
        )
        stats = {
            'Tenders Pending Review': all_tenders_in_institution.filter(status='pending_review').count(),
            'Forwarded to Admin': reviewer_activities.filter(action="Forwarded for Approval").count(),
            'Returned to Creator': reviewer_activities.filter(action="Returned to Creator").count(),
        }
        context['stats'] = stats
        
        # Tenders pending review by anyone, or tenders this reviewer has acted on.
        reviewed_tender_ids = TenderActivity.objects.filter(performed_by=institution_user).values_list('tender_id', flat=True)
        context['tenders'] = all_tenders_in_institution.filter(
            Q(status='pending_review') | Q(id__in=reviewed_tender_ids)
        ).select_related('created_by__user').distinct().order_by(
            # Prioritize 'pending_review' tenders by sorting them first
            Case(When(status='pending_review', then=0), default=1),
            '-updated_at' # Then sort by the most recently updated
        )

    return render(request, "institution/dashboard.html", context)

@login_required
@role_required(allowed_roles=['admin'])
def manage_users(request):
    admin_profile = get_object_or_404(InstitutionUser.objects.select_related('institution'), user=request.user)
    institution = admin_profile.institution

    if request.method == 'POST':
        form = InstitutionUserCreationForm(request.POST)
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
                    InstitutionUser.objects.create(
                        user=new_user,
                        institution=admin_profile.institution,
                        role=form.cleaned_data['role']
                    )
                messages.success(request, f"User '{new_user.username}' created successfully.")
                return redirect('institution:manage_users')
            except IntegrityError:
                form.add_error('username', 'A user with this username or email already exists.')
    else:
        form = InstitutionUserCreationForm()

    # This logic runs for both GET requests and failed POST requests
    users_list = InstitutionUser.objects.filter(institution=institution).exclude(role='admin').select_related('user').order_by('user__first_name', 'user__last_name')

    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    if search_query:
        users_list = users_list.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if role_filter:
        users_list = users_list.filter(role=role_filter)

    if status_filter:
        is_active = status_filter == 'active'
        users_list = users_list.filter(user__is_active=is_active)

    # Pagination
    paginator = Paginator(users_list, 10) # Show 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'institution': institution,
        'users': page_obj,
        'stats': {
            'total': paginator.count, # Use paginator.count for the total after filtering
            'creators': users_list.filter(role='creator').count(),
            'reviewers': users_list.filter(role='reviewer').count(),
        },
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'form': form, # Pass the form instance (either new or with errors)
    }
    return render(request, 'institution/manage_users.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def create_user(request):
    admin_profile = get_object_or_404(InstitutionUser, user=request.user)
    # This view now primarily serves the dedicated "Create User" page, not the modal.
    if request.method == 'POST':
        form = InstitutionUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the base Django User
                    new_user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', '')
                    )
                    # Create the InstitutionUser profile
                    InstitutionUser.objects.create(
                        user=new_user,
                        institution=admin_profile.institution,
                        role=form.cleaned_data['role']
                    )
                messages.success(request, f"User '{new_user.email}' created successfully.")
                return redirect('institution:manage_users')
            except IntegrityError:
                form.add_error(None, "A user with this username or email already exists.")
    else:
        form = InstitutionUserCreationForm()

    context = {
        'form': form,
        'institution_user': admin_profile,
        'role': admin_profile.role,
    }
    return render(request, 'institution/create_user.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def edit_user(request, user_id):
    admin_profile = get_object_or_404(InstitutionUser, user=request.user)
    user_to_edit = get_object_or_404(User, pk=user_id)
    profile_to_edit = get_object_or_404(InstitutionUser, user=user_to_edit)

    # Ensure admin is not editing another admin or a user from another institution
    if profile_to_edit.institution != admin_profile.institution or profile_to_edit.role == 'admin':
        raise Http404

    if request.method == 'POST':
        form = InstitutionUserChangeForm(request.POST, instance=profile_to_edit)
        if form.is_valid():
            # Update the InstitutionUser profile (role)
            form.save()
            # Update the base User model fields
            user_to_edit.first_name = form.cleaned_data['first_name']
            user_to_edit.last_name = form.cleaned_data['last_name']
            user_to_edit.email = form.cleaned_data['email']
            user_to_edit.save()
            messages.success(request, f"User '{user_to_edit.email}' updated successfully.")
            return redirect('institution:manage_users')
    else:
        initial_data = {'first_name': user_to_edit.first_name, 'last_name': user_to_edit.last_name, 'email': user_to_edit.email}
        form = InstitutionUserChangeForm(instance=profile_to_edit, initial=initial_data)

    context = {
        'form': form,
        'user_to_edit': user_to_edit,
        'institution_user': admin_profile,
        'role': admin_profile.role,
    }
    return render(request, 'institution/edit_user.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def delete_user(request, user_id):
    admin_profile = get_object_or_404(InstitutionUser, user=request.user)
    user_to_delete = get_object_or_404(User, pk=user_id)
    profile_to_delete = get_object_or_404(InstitutionUser, user=user_to_delete)

    # Ensure admin is not deleting another admin or a user from another institution
    if profile_to_delete.institution != admin_profile.institution or profile_to_delete.role == 'admin':
        raise Http404

    if request.method == 'POST':
        user_email = user_to_delete.email
        user_to_delete.delete() # Deleting the User will cascade and delete the InstitutionUser profile
        messages.success(request, f"User '{user_email}' has been deleted.")
        return redirect('institution:manage_users')

    context = {
        'user_to_delete': user_to_delete,
        'institution_user': admin_profile,
        'role': admin_profile.role,
    }
    return render(request, 'institution/delete_user_confirm.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def edit_institution_profile(request):
    """Allows an institution admin to edit their own institution's profile."""
    admin_profile = get_object_or_404(InstitutionUser, user=request.user, role='admin')
    institution = admin_profile.institution

    if request.method == 'POST':
        form = InstitutionProfileForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            form.save()
            messages.success(request, "Your institution profile has been updated successfully.")
            return redirect('institution:profile', institution_id=institution.id)
    else:
        form = InstitutionProfileForm(instance=institution)

    context = {
        'form': form,
        'institution': institution,
    }
    return render(request, 'institution/edit_institution_profile.html', context)

def institution_profile(request, institution_id):
    """Displays a public-facing profile for an institution."""
    institution = get_object_or_404(Institution, pk=institution_id)
    context = {
        'institution': institution,
        'is_admin': False,
        'institution_user': None,
        'role': None,
    }
    
    # Check if the logged-in user is the admin of this specific institution
    if request.user.is_authenticated and hasattr(request.user, 'institution_profile'):
        try:
           
            institution_user = InstitutionUser.objects.select_related('institution').get(user=request.user)
            context['institution_user'] = institution_user
            context['role'] = institution_user.role
            
            # Specifically check if the user is an admin of THIS institution
            if institution_user.institution == institution and institution_user.role == 'admin':
                context['is_admin'] = True
        except InstitutionUser.DoesNotExist:
            # User is logged in but has no institution profile, so we do nothing.
            pass

    return render(request, 'institution/institution_profile.html', context)

@login_required
def user_profile(request):
    """Displays the logged-in user's own profile."""
    profile = get_object_or_404(InstitutionUser, user=request.user)
    context = {
        'profile': profile,
    }
    return render(request, 'institution/user_profile.html', context)

@login_required
def edit_user_profile(request):
    """Allows a user to edit their own profile."""
    profile = get_object_or_404(InstitutionUser, user=request.user)
    user = request.user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Save profile-specific fields
            profile = form.save(commit=False)
            
            # Save base user fields
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            
            with transaction.atomic():
                user.save()
                profile.save()

            messages.success(request, "Your profile has been updated successfully.")
            return redirect('institution:user_profile')
    else:
        initial_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        }
        form = UserProfileForm(instance=profile, initial=initial_data)

    context = {
        'form': form,
        'institution_user': profile,
        'role': profile.role,
    }
    return render(request, 'institution/edit_user_profile.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def institution_report(request):
    """Displays institution-specific reports with filters and export options."""
    # Fetch the institution_user to pass to the template for the sidebar
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tenders = Tender.objects.filter(institution=institution_user.institution).exclude(status='draft').order_by('-created_at')

    # Get filter values from request
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date_range', '')

    # Apply filters
    if status_filter:
        tenders = tenders.filter(status=status_filter)
    
    if date_filter:
        try:
            days = int(date_filter)
            start_date = timezone.now() - timezone.timedelta(days=days)
            tenders = tenders.filter(created_at__gte=start_date)
        except (ValueError, TypeError):
            # Handle cases where date_filter is not a valid number
            pass

    # Calculate stats based on the filtered queryset
    stats = tenders.aggregate(
        total_tenders=Count('id'),
        published=Count('id', filter=Q(status='published')),
        completed=Count('id', filter=Q(status='completed')),
        pending=Count('id', filter=Q(status__in=['pending_review', 'pending_approval'])),
    )

    # Pagination
    paginator = Paginator(tenders, 15) # 15 tenders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tenders': page_obj,
        'stats': stats,
        'status_choices': [choice for choice in Tender.STATUS_CHOICES if choice[0] != 'draft'],
        'current_status': status_filter,
        'current_date_range': date_filter,
        'institution_user': institution_user,  # Pass for sidebar logic
        'role': institution_user.role,          # Pass for sidebar logic
    }
    return render(request, 'institution/institution_report.html', context)

def render_to_pdf(template_src, context_dict={}):
    """Helper function to render a Django template to a PDF."""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    # Use UTF-8 encoding
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('We had some errors<pre>%s</pre>' % html, status=500)

@login_required
@role_required(allowed_roles=['admin'])
def generate_report_pdf(request):
    """Generates a PDF report of tenders based on filters."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tenders = Tender.objects.filter(institution=institution_user.institution).exclude(status='draft').order_by('-created_at')

    # Reuse filtering logic from the main report view
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date_range', '')

    if status_filter:
        tenders = tenders.filter(status=status_filter)
    
    if date_filter:
        try:
            days = int(date_filter)
            start_date = timezone.now() - timezone.timedelta(days=days)
            tenders = tenders.filter(created_at__gte=start_date)
        except (ValueError, TypeError):
            pass

    context = {
        'tenders': tenders,
        'institution_name': institution_user.institution.institution_name,
        'report_date': timezone.now(),
        'current_status': status_filter,
        'current_date_range': date_filter,
    }
    
    pdf = render_to_pdf('institution/report_pdf_template.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Tender_Report_{institution_user.institution.institution_name.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF.", status=500)

@login_required
def change_password(request):
    """Allows a user to change their own password."""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Important: update the session with the new password hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('institution:user_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'institution/change_password.html', {'form': form})

@login_required
@role_required(allowed_roles=['admin'])
def list_tenders_for_approval(request):
    """Lists all tenders with 'pending_approval' status for the admin's institution."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tenders = Tender.objects.filter(
        institution=institution_user.institution,
        status='pending_approval'
    ).select_related('created_by__user').order_by('-updated_at')

    context = {'tenders': tenders}
    return render(request, 'institution/list_for_approval.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def verification_submission(request):
    """
    Allows an institution admin to submit or update their verification documents.
    """
    # Correctly fetch the institution through the InstitutionUser profile
    institution_user = get_object_or_404(InstitutionUser, user=request.user, role='admin')
    institution = institution_user.institution

    # If the institution is already approved, redirect them to the dashboard.
    if institution.verification_status == 'approved':
        messages.success(request, "Your institution is verified. Welcome to your dashboard!")
        return redirect('institution:dashboard')

    if request.method == 'POST':
        form = InstitutionVerificationForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            instance = form.save(commit=False)
            # If the institution is submitting for the first time or resubmitting after rejection
            if instance.verification_status in ['not_submitted', 'rejected']:
                instance.verification_status = 'pending'
                instance.verification_remarks = "" # Clear old remarks on resubmission
            instance.save()
            messages.success(request, "Your verification documents have been submitted successfully and are pending review.")
            return redirect('accounts:home')
        else:
            messages.error(request, "Please correct the errors below and resubmit.")
    else:
        form = InstitutionVerificationForm(instance=institution)

    context = {'form': form, 'institution': institution}
    return render(request, 'institution/verification_form.html', context)