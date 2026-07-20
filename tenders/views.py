from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import Http404

from company.models import Company
from institution.models import InstitutionUser
from institution.decorators import role_required
from .models import Tender, Bid
from .forms import TenderForm
from company.views import company_login_required
from .forms import BidSubmissionForm
from institution.models import InstitutionUser

@login_required
@role_required(allowed_roles=['creator'])
def create_tender(request):
    """Allows Creators to create a new tender, saved as a draft."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    if request.method == 'POST':
        form = TenderForm(request.POST, request.FILES)
        if form.is_valid():
            tender = form.save(commit=False)
            tender.institution = institution_user.institution
            tender.created_by = institution_user
            
            action = request.POST.get('action')
            if action == 'send_for_review':
                tender.status = 'pending_review'
                tender.save()
                tender.log_activity(institution_user, "Tender Created and Submitted for Review")
                messages.success(request, f"Tender '{tender.title}' has been created and sent for review.")
            else: # Default to saving as draft
                tender.status = 'draft'
                tender.save()
                tender.log_activity(institution_user, "Tender Created")
                messages.success(request, f"Tender '{tender.title}' created as a draft.")

            return redirect('tenders:tender_detail', tender_id=tender.id)
    else:
        form = TenderForm()
    
    return render(request, 'tenders/create_tender.html', {'form': form})

@login_required
@role_required(allowed_roles=['creator'])
def edit_tender(request, tender_id):
    """Allows a Creator to edit their own tender if it's a draft or has been rejected."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)

    # Security Checks:
    # 1. User must be the original creator.
    # 2. Tender must be in an editable state.
    if tender.created_by != institution_user:
        raise Http404("You can only edit tenders that you have created.")
    if tender.status not in ['draft', 'rejected']:
        messages.error(request, f"This tender cannot be edited as it is currently '{tender.get_status_display()}'.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        form = TenderForm(request.POST, instance=tender)
        if form.is_valid():
            tender = form.save(commit=False)
            action = request.POST.get('action')
            if action == 'send_for_review':
                tender.status = 'pending_review'
                tender.remarks = None # Clear previous rejection remarks
                tender.log_activity(institution_user, "Tender Edited and Submitted for Review")
                messages.success(request, "Tender updated and sent for review.")
            else:
                tender.log_activity(institution_user, "Tender Edited")
                messages.success(request, "Tender has been updated successfully.")
            tender.save()
            return redirect('tenders:tender_detail', tender_id=tender.id)
    else:
        form = TenderForm(instance=tender)
    
    return render(request, 'tenders/edit_tender.html', {'form': form, 'tender': tender})

@login_required
@role_required(allowed_roles=['creator'])
def delete_tender(request, tender_id):
    """Allows a Creator to delete their own tender if it's a draft."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)

    # Security Checks:
    if tender.created_by != institution_user:
        raise Http404("You can only delete tenders that you have created.")
    if tender.status != 'draft':
        messages.error(request, "This tender cannot be deleted as it is no longer a draft.")
        return redirect('tenders:list_tenders')

    if request.method == 'POST':
        tender_title = tender.title
        tender.delete()
        messages.success(request, f"Tender '{tender_title}' has been deleted successfully.")
        return redirect('tenders:list_tenders')

    return render(request, 'tenders/delete_tender_confirm.html', {'tender': tender})

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
    # If no status filter is applied, show all relevant tenders including completed ones.
    # If a filter is applied, use it.
    if not status_filter:
        queryset = queryset.exclude(status__in=['draft', 'archived'])
    elif status_filter:
        queryset = queryset.filter(status=status_filter)

    # Apply 'reviewed by me' filter for reviewers
    reviewed_by_filter = request.GET.get('reviewed_by', '')
    if reviewed_by_filter == 'me' and institution_user.role == 'reviewer':
        # Find all tender IDs where the current reviewer has performed an action
        from .models import TenderActivity
        reviewed_tender_ids = TenderActivity.objects.filter(performed_by=institution_user).values_list('tender_id', flat=True).distinct()
        queryset = queryset.filter(id__in=reviewed_tender_ids)


    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tenders': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Tender.STATUS_CHOICES,
        'reviewed_by_filter': reviewed_by_filter,
    }
    return render(request, 'tenders/list_tenders.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def list_for_approval(request):
    """Displays a list of tenders pending final admin approval."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tenders_for_approval = Tender.objects.filter(institution=institution_user.institution, status='pending_approval').order_by('-updated_at')
    
    context = {'tenders': tenders_for_approval}
    return render(request, 'tenders/review_tenders.html', context)

@login_required
def tender_detail(request, tender_id):
    """Displays tender details and role-specific actions."""
    tender = get_object_or_404(Tender.objects.prefetch_related('bids').select_related('institution', 'created_by__user'), pk=tender_id)
    context = {'tender': tender, 'base_template': 'base.html'}

    # Try to identify the user as an institution member
    institution_user = InstitutionUser.objects.filter(user=request.user).first()

    # Case 1: User is part of the institution that owns the tender
    if institution_user and tender.institution == institution_user.institution:
        # Security: Creators can only see their own drafts.
        if institution_user.role == 'creator' and tender.created_by != institution_user and tender.status == 'draft':
            raise Http404("You can only view your own draft tenders.")

        context['activities'] = tender.activities.all().select_related('performed_by__user')
        context['role'] = institution_user.role
        if institution_user.role == 'admin':
            context['bids'] = tender.bids.all().select_related('company')
        else:
            context['bids'] = [] # Non-admin institution users cannot see bids
        return render(request, 'tenders/tender_detail.html', context)

    # Case 2: User is a company user
    if hasattr(request.user, 'company'):
        company = request.user.company
        existing_bid = Bid.objects.filter(tender=tender, company=company).first()

        # If the tender is published and the company has not bid yet,
        # redirect them directly to the submission page.
        if tender.status == 'published' and not existing_bid:
            return redirect('tenders:submit_bid', tender_id=tender.id)

        # Security: Company users can only see published or expired tenders.
        if tender.status not in ['published', 'expired']:
            raise Http404("This tender is not available for public viewing.")
        
        
        context['existing_bid'] = existing_bid
        # Company users don't see the internal activity log
        context['activities'] = [] 
        context['bids'] = [] # Companies cannot see other companies' bids
        return render(request, 'tenders/tender_detail.html', context)

    # Case 3: User is anonymous or has no relation to the tender
    if tender.status not in ['published', 'expired']:
        raise Http404("This tender is not available for public viewing.")
    
    context['activities'] = [] # Anonymous users don't see activities
    context['bids'] = [] # Anonymous users don't see bids
    return render(request, 'tenders/tender_detail.html', context)
    
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
                return redirect('tenders:tender_detail', tender_id=tender.id)
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
                return redirect('tenders:tender_detail', tender_id=tender.id)
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
        return redirect('tenders:tender_detail', tender_id=tender.id)

    tender.save()
    return redirect('tenders:tender_detail', tender_id=tender.id)

@login_required
@role_required(allowed_roles=['admin'])
def list_archived_tenders(request):
    """Displays a list of all archived tenders."""
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    archived_tenders = Tender.objects.filter(institution=institution_user.institution, status='archived').order_by('-updated_at')
    return render(request, 'tenders/list_archived_tenders.html', {'tenders': archived_tenders})


# --- Bidding Views ---
 # Ensure InstitutionUser is imported

@company_login_required
def submit_bid(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id, status='published')
    company = get_object_or_404(Company, user=request.user)

    # Check if the tender deadline has passed
    if tender.deadline and tender.deadline < timezone.now():
        messages.error(request, "The deadline for this tender has passed. You cannot submit a bid.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    if Bid.objects.filter(tender=tender, company=company).exists():
        # If a bid already exists, redirect to bid_detail to allow viewing/editing (if allowed)
        existing_bid = Bid.objects.get(tender=tender, company=company)
        messages.info(request, "You have already submitted a bid for this tender. Redirecting to your bid details.")
        return redirect('tenders:bid_detail', bid_id=existing_bid.id)

    if request.method == 'POST':
        # Server-side validation for the terms agreement checkbox
        if 'terms_agreement' not in request.POST:
            messages.error(request, "You must agree to the Terms & Conditions to place a bid.")
            return redirect('tenders:submit_bid', tender_id=tender.id)

        form = BidSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.tender = tender
            bid.company = company
            bid.save()
            messages.success(request, "Your bid has been submitted successfully.")
            return redirect('tenders:my_bids')
    else:
        form = BidSubmissionForm()

    context = {
        'form': form,
        'tender': tender,
    }
    return render(request, 'tenders/submit_bid.html', context)

@company_login_required
def my_bids(request):
    company = get_object_or_404(Company, user=request.user)
    bids = Bid.objects.filter(company=company).select_related('tender', 'tender__institution').order_by('-submitted_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        bids = bids.filter(status=status_filter)

    context = {
        'bids': bids,
        'status_choices': Bid.STATUS_CHOICES,
        'status_filter': status_filter,
    }
    return render(request, 'tenders/my_bids.html', context)

# Removed @company_login_required as it needs to be accessible by admins too
def bid_detail(request, bid_id):
    bid = get_object_or_404(Bid.objects.select_related('tender', 'company', 'tender__institution'), pk=bid_id)

    # Ensure user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to view bid details.")
        return redirect('accounts:login_page')

    # Case 1: User is a company user
    if hasattr(request.user, 'company'):
        company = request.user.company
        if bid.company == company:
            return render(request, 'tenders/bid_detail.html', {'bid': bid})
        else:
            messages.error(request, "You do not have permission to view this bid.")
            return redirect('company:dashboard')
    
    # Case 2: User is an institution user
    elif hasattr(request.user, 'institution_profile'):
        institution_user = request.user.institution_profile
        # Check if the institution user belongs to the institution that owns the tender
        if bid.tender.institution == institution_user.institution:
            # Only admin role can view bid details
            if institution_user.role == 'admin':
                return render(request, 'tenders/bid_detail.html', {'bid': bid})
            else:
                messages.error(request, "You do not have permission to view bid details.")
                return redirect('tenders:tender_detail', tender_id=bid.tender.id) # Redirect to tender detail
        else:
            messages.error(request, "You do not have permission to view bids for this institution.")
            return redirect('institution:dashboard')

    # Case 3: User is authenticated but neither company nor institution
    messages.error(request, "You do not have permission to view this page.")
    return redirect('accounts:home')

@login_required
@role_required(allowed_roles=['admin'])
def update_bid_status(request, bid_id):
    """Allows institution admins to update the status of a bid."""
    if request.method != 'POST':
        return redirect('accounts:home') # Or an appropriate error page

    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    bid = get_object_or_404(Bid.objects.select_related('tender__institution'), pk=bid_id)

    # Ensure the admin belongs to the institution that owns the tender
    if bid.tender.institution != institution_user.institution:
        messages.error(request, "You do not have permission to manage bids for this tender.")
        return redirect('tenders:tender_detail', tender_id=bid.tender.id)

    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '').strip()

    if action == 'accept_bid':
        tender = bid.tender
        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # 1. Accept the current bid
            bid.status = 'accepted'
            bid.save()
    
            # 2. Reject all other bids for this tender
            other_bids = tender.bids.exclude(pk=bid.id).filter(status__in=['submitted', 'under_review', 'shortlisted'])
            other_bids.update(status='rejected')
    
            # 3. Update the tender status to 'completed'
            tender.status = 'completed'
            tender.save()
            tender.log_activity(institution_user, f"Bid from {bid.company.company_name} accepted. Tender completed.", remarks=remarks)
        messages.success(request, f"Bid from {bid.company.company_name} has been accepted and the tender is now marked as completed.")
    
    elif action == 'reject_bid':
        if not remarks:
            messages.error(request, "Remarks are mandatory when rejecting a bid.")
            return redirect('tenders:bid_detail', bid_id=bid.id)
        bid.status = 'rejected'
        bid.save()
        messages.info(request, f"The bid from {bid.company.company_name} has been rejected.")
        # Log activity for the tender
        bid.tender.log_activity(institution_user, f"Bid Rejected: {bid.company.company_name}", remarks=remarks)
    else:
        messages.error(request, "Invalid action for bid status update.")
        return redirect('tenders:bid_detail', bid_id=bid.id)
    
    return redirect('tenders:bid_detail', bid_id=bid.id)

@login_required
def tender_report(request):
    """Displays tender reports with filters and export options."""
    # This view will contain logic for filtering and generating report data.
    # Access control should be implemented based on user role.
    return render(request, 'tenders/tender_report.html')