from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.http import Http404
from institution.decorators import role_required
from .models import Tender, Bid
from .forms import TenderForm
from company.views import company_login_required
from .forms import BidSubmissionForm
from institution.models import InstitutionUser
from company.models import Company

@login_required
@role_required(allowed_roles=['creator', 'admin'])
def create_tender(request):
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    if request.method == 'POST':
        form = TenderForm(request.POST, request.FILES)
        if form.is_valid():
            tender = form.save(commit=False)
            tender.institution = institution_user.institution
            tender.created_by = institution_user
            
            # Determine status based on which button was clicked
            if 'submit_for_review' in request.POST:
                tender.status = 'pending_review'
                tender.save()
                tender.log_activity(institution_user, "Tender Created and Submitted for Review")
                messages.success(request, f"Tender '{tender.title}' has been created and sent for review.")
            else: # Default to saving as draft
                tender.status = 'draft'
                tender.save()
                tender.log_activity(institution_user, "Tender Saved as Draft")
                messages.info(request, f"Tender '{tender.title}' has been saved as a draft.")
            
            return redirect('institution:dashboard')
    else:
        form = TenderForm()
    return render(request, 'tenders/create_tender.html', {'form': form})

@login_required
def tender_detail(request, tender_id):
    tender = get_object_or_404(Tender.objects.select_related('institution', 'created_by__user'), pk=tender_id)
    
    # Determine user's role and relationship to the tender
    user_role = None
    is_creator = False
    is_reviewer = False
    is_admin = False
    is_company = False
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'institution_profile'):
            profile = request.user.institution_profile
            if profile.institution == tender.institution:
                user_role = profile.role
                if user_role == 'creator' and tender.created_by == profile:
                    is_creator = True
                if user_role == 'reviewer':
                    is_reviewer = True
                if user_role == 'admin':
                    is_admin = True
        elif hasattr(request.user, 'company'):
            is_company = True

    # Permissions check
    if tender.status == 'draft' and not (is_creator or is_admin):
        raise Http404("Tender not found.")

    # Get related data
    activities = tender.activities.select_related('performed_by__user').order_by('-timestamp')
    bids = tender.bids.select_related('company').order_by('-submitted_at')

    context = {
        'tender': tender,
        'activities': activities,
        'bids': bids,
        'user_role': user_role,
        'is_creator': is_creator,
        'is_reviewer': is_reviewer,
        'is_admin': is_admin,
        'is_company': is_company,
        'now': timezone.now(),
    }
    return render(request, 'tenders/tender_detail.html', context)

@login_required
@role_required(allowed_roles=['creator', 'admin'])
def edit_tender(request, tender_id):
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)

    # Permission check: Only creator or admin can edit.
    # Creator can only edit if it's a draft or was rejected.
    is_admin = institution_user.role == 'admin'
    is_creator = tender.created_by == institution_user

    if not (is_admin or (is_creator and tender.status in ['draft', 'rejected'])):
        messages.error(request, "You do not have permission to edit this tender in its current state.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        form = TenderForm(request.POST, request.FILES, instance=tender)
        if form.is_valid():
            updated_tender = form.save(commit=False)
            
            if 'submit_for_review' in request.POST:
                updated_tender.status = 'pending_review'
                updated_tender.remarks = "" # Clear previous rejection remarks
                updated_tender.log_activity(institution_user, "Resubmitted for Review")
                messages.success(request, "Tender has been updated and resubmitted for review.")
            else:
                updated_tender.log_activity(institution_user, "Tender Details Edited")
                messages.success(request, "Tender draft has been updated.")
            
            updated_tender.save()
            return redirect('tenders:tender_detail', tender_id=tender.id)
    else:
        form = TenderForm(instance=tender)

    context = {
        'form': form,
        'tender': tender,
    }
    return render(request, 'tenders/edit_tender.html', context)

@login_required
@role_required(allowed_roles=['reviewer', 'admin'])
def update_tender_status(request, tender_id):
    if request.method != 'POST':
        return redirect('institution:dashboard')

    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)
    
    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '').strip()
    current_status = tender.status
    action_performed = False

    # --- Reviewer Actions ---
    if institution_user.role == 'reviewer':
        if action == 'send_to_admin' and current_status == 'pending_review':
            tender.status = 'pending_approval'
            tender.log_activity(institution_user, "Forwarded for Approval")
            messages.success(request, "Tender forwarded for final approval.")
            action_performed = True
        elif action == 'return_to_creator' and current_status == 'pending_review':
            if not remarks:
                messages.error(request, "Remarks are mandatory when returning a tender.")
                return redirect('tenders:tender_detail', tender_id=tender.id)
            tender.return_to_creator(institution_user, remarks)
            messages.warning(request, "Tender returned to creator with remarks.")
            action_performed = True

    # --- Admin Actions ---
    if institution_user.role == 'admin':
        if action == 'publish' and current_status == 'pending_approval':
            tender.status = 'published'
            tender.log_activity(institution_user, "Approved and Published")
            messages.success(request, "Tender has been approved and published.")
            action_performed = True
        elif action == 'reject_by_admin' and current_status == 'pending_approval':
            if not remarks:
                messages.error(request, "Remarks are mandatory when rejecting a tender.")
                return redirect('tenders:tender_detail', tender_id=tender.id)
            tender.reject_by_admin(institution_user, remarks)
            messages.warning(request, "Tender has been rejected and returned to the creator.")
            action_performed = True

    if action_performed:
        tender.save()
    else:
        messages.error(request, "Invalid action or you do not have permission to perform this action.")

    return redirect('tenders:tender_detail', tender_id=tender.id)

@company_login_required
def submit_bid(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id, status='published')
    company = get_object_or_404(Company, user=request.user)

    # Check if bidding is open
    now = timezone.now()
    if tender.opening_date and now < tender.opening_date:
        messages.error(request, "Bidding for this tender has not opened yet.")
        return redirect('tenders:tender_detail', tender_id=tender.id)
    if tender.deadline and now > tender.deadline:
        messages.error(request, "The deadline for this tender has passed.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    # Check if company has already bid
    if Bid.objects.filter(tender=tender, company=company).exists():
        messages.warning(request, "You have already submitted a bid for this tender.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    if request.method == 'POST':
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
    bids = Bid.objects.filter(company=company).select_related('tender').order_by('-submitted_at')
    context = {
        'bids': bids,
    }
    return render(request, 'tenders/my_bids.html', context)

@login_required
def bid_detail(request, bid_id):
    bid = get_object_or_404(Bid.objects.select_related('tender', 'company', 'tender__institution'), pk=bid_id)
    
    # Permissions check
    is_institution_user = hasattr(request.user, 'institution_profile') and request.user.institution_profile.institution == bid.tender.institution
    is_company_user = hasattr(request.user, 'company') and request.user.company == bid.company

    if not (is_institution_user or is_company_user):
        raise Http404

    context = {
        'bid': bid,
        'is_institution_user': is_institution_user,
        'is_company_user': is_company_user,
    }
    return render(request, 'tenders/bid_detail.html', context)

@login_required
@role_required(allowed_roles=['admin'])
def update_bid_status(request, bid_id):
    if request.method != 'POST':
        return redirect('institution:dashboard')

    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    bid = get_object_or_404(Bid, pk=bid_id)
    tender = bid.tender

    # Ensure the admin belongs to the correct institution
    if tender.institution != institution_user.institution:
        messages.error(request, "You do not have permission to modify this bid.")
        return redirect('tenders:bid_detail', bid_id=bid.id)

    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '')

    if action == 'accept':
        with transaction.atomic():
            # 1. Accept the current bid
            bid.status = 'accepted'
            bid.save()
    
            # 2. Reject all other bids for this tender
            other_bids = tender.bids.exclude(pk=bid.id).filter(status__in=['submitted', 'under_review', 'shortlisted'])
            for other_bid in other_bids:
                other_bid.status = 'rejected'
                other_bid.save()
    
            # 3. Update the tender status to 'completed'
            tender.status = 'completed'
            tender.save()
    
            # 4. Log activities
            tender.log_activity(institution_user, f"Bid Accepted: {bid.company.company_name}", remarks=remarks)
            messages.success(request, f"Bid from {bid.company.company_name} has been accepted. The tender is now completed.")

    elif action == 'reject':
        if bid.status == 'accepted':
            messages.error(request, "Cannot reject a bid that has already been accepted.")
            return redirect('tenders:bid_detail', bid_id=bid.id)
        bid.status = 'rejected'
        bid.save()
        messages.info(request, f"The bid from {bid.company.company_name} has been rejected.")
        # Log activity for the tender
        bid.tender.log_activity(institution_user, f"Bid Rejected: {bid.company.company_name}", remarks=remarks)

    else:
        messages.error(request, "Invalid action.")

    return redirect('tenders:bid_detail', bid_id=bid.id)