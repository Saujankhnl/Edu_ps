from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import Http404
from institution.decorators import role_required
from .models import Tender, Bid, TenderActivity
from .forms import TenderForm
from company.views import company_login_required
from .forms import BidSubmissionForm
from institution.models import InstitutionUser
from django.http import HttpResponse
from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa

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
            if request.POST.get('action') == 'send_for_review':
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
    
    context = {
        'form': form,
        'institution_user': institution_user,
        'role': institution_user.role,
    }
    return render(request, 'tenders/create_tender.html', context)

@login_required
def tender_detail(request, tender_id):
    tender = get_object_or_404(Tender.objects.select_related('institution', 'created_by__user'), pk=tender_id)
    
    # Determine user's role and relationship to the tender
    user_role = None
    is_creator = False
    is_reviewer = False
    is_admin = False
    is_company = False
    company_verification_status = None
    
    if hasattr(request.user, 'institution_profile'):
        profile = request.user.institution_profile
        if profile.institution == tender.institution:
            user_role = profile.role
            is_creator = (user_role == 'creator' and tender.created_by == profile)
            is_reviewer = (user_role == 'reviewer')
            is_admin = (user_role == 'admin')
    elif hasattr(request.user, 'company'):
        is_company = True
        company_verification_status = request.user.company.verification_status

    # Permissions check
    # Only the creator or an admin can see a tender while it's a draft.
    if tender.status == 'draft' and not (is_creator or is_admin):
        raise Http404("Tender not found.")

    # Check if the company user has already bid
    has_bid = False
    if is_company:
        has_bid = Bid.objects.filter(tender=tender, company=request.user.company).exists()

    # Get related data
    activities = tender.activities.select_related('performed_by__user').order_by('-timestamp')
    bids = tender.bids.select_related('company').order_by('-submitted_at')

    context = {
        'tender': tender,
        'activities': activities,
        'bids': bids,
        'role': user_role, # Add role to the context
        'user_role': user_role,
        'is_creator': is_creator,
        'is_reviewer': is_reviewer,
        'is_admin': is_admin,
        'is_company': is_company,
        'company_verification_status': company_verification_status,
        'has_bid': has_bid,
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
            
            if request.POST.get('action') == 'send_for_review':
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
@role_required(allowed_roles=['creator', 'admin'])
def delete_tender(request, tender_id):
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tender = get_object_or_404(Tender, pk=tender_id, institution=institution_user.institution)

    # Permission check: Only creator (if draft) or admin can delete.
    is_admin = institution_user.role == 'admin'
    is_creator = tender.created_by == institution_user

    if not (is_admin or (is_creator and tender.status == 'draft')):
        messages.error(request, "You do not have permission to delete this tender.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        tender_title = tender.title
        tender.delete()
        messages.success(request, f"Tender '{tender_title}' has been successfully deleted.")
        return redirect('institution:dashboard')

    return render(request, 'tenders/delete_tender_confirm.html', {'tender': tender})

@login_required
@role_required(allowed_roles=['creator', 'reviewer', 'admin'])
def list_tenders(request):
    institution_user = get_object_or_404(InstitutionUser, user=request.user)
    tenders_list = Tender.objects.filter(institution=institution_user.institution).order_by('-updated_at')

    # Filtering logic
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    reviewed_by_filter = request.GET.get('reviewed_by', '')

    if search_query:
        tenders_list = tenders_list.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    if reviewed_by_filter == 'me' and institution_user.role == 'reviewer':
        # Get IDs of tenders this user has logged an activity for
        reviewed_tender_ids = TenderActivity.objects.filter(
            performed_by=institution_user
        ).values_list('tender_id', flat=True).distinct()
        
        # Filter the main tender list to only these tenders
        tenders_list = tenders_list.filter(id__in=reviewed_tender_ids)

    if status_filter:
        tenders_list = tenders_list.filter(status=status_filter)

    # Pagination
    paginator = Paginator(tenders_list, 10) # Show 10 tenders per page
    page_number = request.GET.get('page')
    tenders = paginator.get_page(page_number)

    context = {
        'tenders': tenders,
        'status_choices': Tender.STATUS_CHOICES,
        'search_query': search_query,
        'status_filter': status_filter,
        'reviewed_by_filter': reviewed_by_filter,
        'institution_user': institution_user,
        'role': institution_user.role,
    }
    return render(request, 'tenders/list_tenders.html', context)



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

    # --- Creator Actions ---
    if institution_user.role == 'creator' and tender.created_by == institution_user:
        if action == 'submit_for_review' and current_status in ['draft', 'rejected']:
            tender.status = 'pending_review'
            tender.remarks = "" # Clear previous rejection remarks
            tender.log_activity(institution_user, "Resubmitted for Review")
            messages.success(request, "Tender has been resubmitted for review.")
            action_performed = True

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

    # Ensure the company is verified before allowing them to bid.
    # The company dashboard already handles routing to the verification page if needed.
    if company.verification_status != 'approved':
        messages.error(request, "Your company profile must be verified before you can submit bids. Please complete your verification process.")
        return redirect('company:dashboard')

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
    
    institution_user = None
    is_institution_user = False
    is_company_user = False

    # Permissions check
    if hasattr(request.user, 'institution_profile'):
        institution_user = request.user.institution_profile
        if institution_user.institution == bid.tender.institution:
            is_institution_user = True
    elif hasattr(request.user, 'company'):
        if request.user.company == bid.company:
            is_company_user = True

    if not (is_institution_user or is_company_user):
        raise Http404

    # Determine if the bid is in a state where an admin can take action
    can_admin_act = False
    if is_institution_user and institution_user.role == 'admin':
        can_admin_act = bid.status in ['submitted', 'under_review', 'shortlisted']

    context = {
        'bid': bid,
        'institution_user': institution_user,
        'is_institution_user': is_institution_user,
        'is_company_user': is_company_user,
        'can_admin_act': can_admin_act,
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

    # Critical Permission Check: Only allow actions on bids for 'published' or 'completed' tenders.
    if tender.status not in ['published', 'completed']:
        messages.error(request, f"Actions on bids are not allowed as the tender is not in 'Published' state. Current state: {tender.get_status_display()}.")
        return redirect('tenders:bid_detail', bid_id=bid.id)

    # Ensure the admin belongs to the correct institution
    if tender.institution != institution_user.institution:
        messages.error(request, "You do not have permission to modify this bid.")
        return redirect('tenders:bid_detail', bid_id=bid.id)

    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '')

    if action == 'accept_bid':
        try:
            with transaction.atomic():
                # 1. Update the tender status to 'completed' first.
                tender.status = 'completed'
                tender.save()

                # 2. Accept the winning bid.
                bid.status = 'accepted'
                bid.save()

                # 3. Reject all other open bids for this tender.
                tender.bids.exclude(pk=bid.id).filter(status__in=['submitted', 'under_review', 'shortlisted']).update(status='rejected')

                # 4. Log the primary success activity.
                tender.log_activity(institution_user, f"Bid from {bid.company.company_name} was accepted.", remarks=remarks)

            messages.success(request, f"Successfully accepted the bid from {bid.company.company_name}. The tender is now marked as completed.")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")

    elif action == 'reject_bid':
        if bid.status == 'accepted':
            messages.error(request, "This bid has already been accepted. You cannot reject a winning bid directly.")
            return redirect('tenders:bid_detail', bid_id=bid.id)
        bid.status = 'rejected'
        bid.save()
        messages.info(request, f"The bid from {bid.company.company_name} has been rejected.")
        # Log activity for the tender
        bid.tender.log_activity(institution_user, f"Bid Rejected: {bid.company.company_name}", remarks=remarks)

    else:
        messages.error(request, "Invalid action.")

    return redirect('tenders:bid_detail', bid_id=bid.id)

def render_to_pdf(template_src, context_dict={}):
    """Helper function to render a Django template to a PDF."""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

@login_required
@role_required(allowed_roles=['admin'])
def generate_tender_pdf(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id)
    context = {'tender': tender, 'report_date': timezone.now()}
    pdf = render_to_pdf('tenders/tender_detail_pdf.html', context)
    if pdf:
        return pdf
    messages.error(request, "Could not generate PDF report.")
    return redirect('tenders:tender_detail', tender_id=tender.id)

@login_required
@role_required(allowed_roles=['admin'])
def generate_bids_pdf(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id)
    bids = tender.bids.select_related('company').order_by('submitted_at')
    context = {'tender': tender, 'bids': bids, 'report_date': timezone.now()}
    pdf = render_to_pdf('tenders/bids_report_pdf.html', context)
    if pdf:
        return pdf
    messages.error(request, "Could not generate Bids PDF report.")
    return redirect('tenders:tender_detail', tender_id=tender.id)