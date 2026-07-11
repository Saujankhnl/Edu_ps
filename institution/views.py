from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from .models import Institution, InstitutionUser, Tender, TenderActivity
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When
from django.http import HttpResponseForbidden, Http404
from django.db import transaction, IntegrityError
from django.contrib import messages
from .decorators import role_required 
from .forms import InstitutionUserCreationForm, InstitutionUserChangeForm, TenderForm, InstitutionProfileForm, UserProfileForm, PasswordChangeForm
from django.utils import timezone


@login_required
def dashboard(request):
    try:
        institution_user = InstitutionUser.objects.get(user=request.user)
        institution = institution_user.institution
        role = institution_user.role
    except InstitutionUser.DoesNotExist:
        return render(request, 'institution/error_no_profile.html')

    # Base querysets
    all_tenders_in_institution = Tender.objects.filter(institution=institution)
    
    # Auto-expire tenders
    expired_tenders = all_tenders_in_institution.filter(status='published', deadline__lt=timezone.now())
    if expired_tenders.exists():
        expired_count = expired_tenders.update(status='expired')
        # Log this action for the first expired tender as a sample
        if expired_count > 0:
            sample_tender = expired_tenders.first()
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
            archived=Count('id', filter=Q(status='archived')),
            expired=Count('id', filter=Q(status='expired')),
        )
        stats['total_users'] = InstitutionUser.objects.filter(institution=institution).count()
        context['stats'] = stats
        context['chart_data'] = {
            'labels': ['Published', 'Pending Approval', 'Rejected', 'Archived', 'Expired'],
            'data': [stats['published'], stats['pending_approval'], stats['rejected'], stats['archived'], stats['expired']],
        }
        context['tenders'] = all_tenders_in_institution.order_by('-updated_at')

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
        stats = all_tenders_in_institution.aggregate(
            pending_review=Count('id', filter=Q(status='pending_review')),
        )
        stats['reviewed_count'] = TenderActivity.objects.filter(performed_by=institution_user, action__in=["Forwarded for Approval", "Returned to Creator"]).count()
        context['stats'] = stats
        context['tenders'] = all_tenders_in_institution.filter(status__in=['pending_review', 'pending_approval', 'approved', 'published', 'rejected']).order_by('-updated_at')

    return render(request, "institution/dashboard.html", context)

@login_required
@role_required(allowed_roles=['admin'])
def manage_users(request):
    admin_user_profile = get_object_or_404(InstitutionUser.objects.select_related('institution'), user=request.user)
    institution = admin_user_profile.institution
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

    # ***FIX***: Calculate stats on the filtered list *before* pagination
    stats = users_list.aggregate(
        total=Count('id'),
        creators=Count('id', filter=Q(role='creator')),
        reviewers=Count('id', filter=Q(role='reviewer')),
    )

    # Pagination
    paginator = Paginator(users_list, 10) # Show 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'institution': institution,
        'users': page_obj,
        'stats': stats,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    return render(request, 'institution/manage_users.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def create_user(request):
    admin_profile = get_object_or_404(InstitutionUser, user=request.user)

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
                messages.error(request, "A user with this email already exists.")
    else:
        form = InstitutionUserCreationForm()

    return render(request, 'institution/create_user.html', {'form': form})

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

    return render(request, 'institution/edit_user.html', {'form': form, 'user_to_edit': user_to_edit})

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

    return render(request, 'institution/delete_user_confirm.html', {'user_to_delete': user_to_delete})

@login_required
@role_required(allowed_roles=['creator'])
def create_tender(request):
    """Allows Creators to create a new tender, saved as a draft."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    if request.method == 'POST':
        form = TenderForm(request.POST)
        if form.is_valid():
            tender = form.save(commit=False)
            tender.institution = institution_user.institution
            tender.created_by = institution_user
            tender.status = 'draft' # Always start as a draft
            tender.save()
            tender.log_activity(institution_user, "Tender Created")
            messages.success(request, f"Tender '{tender.title}' created as a draft.")
            return redirect('institution:tender_detail', tender_id=tender.id)
    else:
        form = TenderForm()
    
    return render(request, 'institution/create_tender.html', {'form': form})

@login_required
def list_tenders(request):
    """Displays a searchable and filterable list of all tenders in the institution."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    
    queryset = Tender.objects.filter(institution=institution_user.institution).order_by('-updated_at')

    # Apply search
    search_query = request.GET.get('q', '')
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tenders': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Tender.STATUS_CHOICES,
    }
    return render(request, 'institution/list_tenders.html', context)


@login_required
def tender_detail(request, tender_id):
    """Displays tender details and role-specific actions."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)
    activities = tender.activities.all().select_related('performed_by__user')

    # Security check: Creators can only see their own tenders
    if institution_user.role == 'creator' and tender.created_by != institution_user:
        raise Http404

    context = {
        'tender': tender,
        'activities': activities,
        'role': institution_user.role,
    }
    return render(request, 'institution/tender_detail.html', context)

@login_required
def update_tender_status(request, tender_id):
    """Handles all status changes for a tender based on user role and action."""
    if request.method != 'POST':
        return redirect('institution:dashboard')

    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)
    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '')

    role = institution_user.role
    current_status = tender.status

    # Creator Actions
    if role == 'creator' and tender.created_by == institution_user:
        if action == 'submit_for_review' and current_status in ['draft', 'rejected']:
            tender.status = 'pending_review'
            tender.remarks = None # Clear previous remarks on resubmission
            tender.log_activity(institution_user, "Submitted for Review")
            messages.success(request, "Tender submitted for review.")

    # Reviewer Actions
    elif role == 'reviewer':
        if action == 'send_to_admin' and current_status == 'pending_review':
            tender.status = 'pending_approval'
            tender.log_activity(institution_user, "Forwarded for Approval")
            messages.success(request, "Tender forwarded for final approval.")
        elif action == 'return_to_creator' and current_status == 'pending_review':
            if not remarks:
                messages.error(request, "Remarks are mandatory when returning a tender.")
                return redirect('institution:tender_detail', tender_id=tender.id)
            tender.status = 'rejected'
            tender.remarks = remarks
            tender.log_activity(institution_user, "Returned to Creator", remarks=remarks)
            messages.warning(request, "Tender returned to creator with remarks.")

    # Admin Actions
    elif role == 'admin':
        if action == 'publish' and current_status == 'pending_approval':
            tender.status = 'published'
            tender.log_activity(institution_user, "Approved and Published")
            messages.success(request, "Tender has been approved and published.")
        elif action == 'reject' and current_status == 'pending_approval':
            if not remarks:
                messages.error(request, "Remarks are mandatory when rejecting a tender.")
                return redirect('institution:tender_detail', tender_id=tender.id)
            tender.status = 'rejected'
            tender.remarks = remarks
            tender.log_activity(institution_user, "Rejected", remarks=remarks)
            messages.error(request, "Tender has been rejected and returned to the creator.")
        
        elif action == 'archive' and current_status not in ['archived', 'draft']:
            tender.status = 'archived'
            tender.log_activity(institution_user, "Tender Archived")
            messages.info(request, "Tender has been archived.")

    else:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('institution:tender_detail', tender_id=tender.id)

    tender.save()
    return redirect('institution:tender_detail', tender_id=tender.id)

@login_required
@role_required(allowed_roles=['admin'])
def list_archived_tenders(request):
    """Displays a list of all archived tenders."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    archived_tenders = Tender.objects.filter(institution=institution_user.institution, status='archived').order_by('-updated_at')
    return render(request, 'institution/list_archived_tenders.html', {'tenders': archived_tenders})

def institution_profile(request, institution_id):
    """Displays a public-facing profile for an institution."""
    institution = get_object_or_404(Institution, pk=institution_id)
    
    # Check if the logged-in user is the admin of this specific institution
    is_admin = False
    if request.user.is_authenticated and hasattr(request.user, 'institution_profile'):
        if request.user.institution_profile.institution == institution and request.user.institution_profile.role == 'admin':
            is_admin = True

    context = {
        'institution': institution,
        'is_admin': is_admin,
    }
    return render(request, 'institution/institution_profile.html', context)

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

@login_required
def user_profile(request):
    """Displays the logged-in user's own profile."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    return render(request, 'institution/user_profile.html', {'profile': institution_user})

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

    return render(request, 'institution/edit_user_profile.html', {'form': form})

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