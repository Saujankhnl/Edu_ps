from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import Http404
from institution.decorators import role_required
from .models import Tender, Bid, TenderActivity
from .forms import TenderForm, BidSubmissionForm
from company.decorators import company_role_required
from institution.models import InstitutionUser
from django.http import HttpResponse
from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa

from company.models import Company
from company.decorators import company_login_required

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
    institution_user = None
    company_verification_status = None
    
    # Check if the user is an institution user (and is authenticated)
    if request.user.is_authenticated and hasattr(request.user, 'institution_profile'):
        profile = request.user.institution_profile
        if profile.institution == tender.institution:
            institution_user = profile
            user_role = profile.role
            is_creator = (user_role == 'creator' and tender.created_by == profile)
            is_reviewer = (user_role == 'reviewer')
            is_admin = (user_role == 'admin')
    # Check if the user is a company user
    elif request.user.is_authenticated and hasattr(request.user, 'company'):
        is_company = True
        company_profile = request.user.company
        user_role = company_profile.role # Correctly assign the company user's role
        company_verification_status = company_profile.verification_status

    # Permissions check
    # Only the creator or an admin can see a tender while it's a draft.
    if tender.status == 'draft' and not (is_creator or is_admin):
        raise Http404("Tender not found.")

    # Check if the company user has already bid (any status)
    existing_bid = None
    if is_company:
        existing_bid = Bid.objects.filter(tender=tender, company=request.user.company).first()

    # Get related data
    activities = tender.activities.select_related('performed_by__user').order_by('-timestamp')
    bids = tender.bids.select_related('company').order_by('-submitted_at')

    context = {
        'tender': tender,
        'activities': activities,
        'bids': bids,
        'role': user_role, # Add role to the context
        'institution_user': institution_user,
        'user_role': user_role,
        'is_creator': is_creator,
        'is_reviewer': is_reviewer,
        'is_admin': is_admin,
        'is_company': is_company,
        'company_verification_status': company_verification_status,
        'existing_bid': existing_bid, # Pass the existing bid object
        'now': timezone.now(),
    }
    return render(request, 'tenders/tender_detail.html', context)


@login_required
@role_required(allowed_roles=['creator', 'admin', 'reviewer'])
def edit_tender(request, tender_id):

    institution_user = get_object_or_404(
        InstitutionUser,
        user=request.user
    )

    tender = get_object_or_404(
        Tender,
        pk=tender_id,
        institution=institution_user.institution
    )

    is_admin = institution_user.role == 'admin'
    is_creator = tender.created_by == institution_user

    if not (
        is_admin
        or (
            is_creator
            and tender.status in ['draft', 'rejected']
        )
    ):
        messages.error(
            request,
            "You do not have permission to edit this tender."
        )

        return redirect(
            'tenders:tender_detail',
            tender_id=tender.id
        )

    if request.method == 'POST':

        print("========== EDIT TENDER ==========")
        print("POST RECEIVED")
        print(request.POST)

        form = TenderForm(
            request.POST,
            request.FILES,
            instance=tender
        )

        print("FORM VALID:", form.is_valid())
        print("FORM ERRORS:", form.errors)

        if form.is_valid():

            updated_tender = form.save(commit=False)

            action = request.POST.get('action')

            if action == 'send_for_review':

                updated_tender.status = 'pending_review'
                updated_tender.remarks = ""

                updated_tender.save()

                updated_tender.log_activity(
                    institution_user,
                    "Resubmitted for Review"
                )

                messages.success(
                    request,
                    "Tender has been resubmitted for review."
                )

            else:

                updated_tender.save()

                updated_tender.log_activity(
                    institution_user,
                    "Tender Details Edited"
                )

                messages.success(
                    request,
                    "Tender has been updated."
                )

            return redirect(
                'tenders:tender_detail',
                tender_id=tender.id
            )

    else:

        form = TenderForm(instance=tender)

    return render(
        request,
        'tenders/edit_tender.html',
        {
            'form': form,
            'tender': tender,
        }
    )

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
@role_required(allowed_roles=['creator', 'admin', 'reviewer'])
def update_tender_status(request, tender_id):

    tender = get_object_or_404(Tender, id=tender_id)

    action = request.POST.get("action")
    remarks = request.POST.get("remarks", "").strip()

    print("\n========== UPDATE TENDER STATUS ==========")
    print("USER:", request.user.username)
    print("ROLE:", request.user.institution_profile.role)
    print("TENDER:", tender.title)
    print("STATUS:", tender.status)
    print("ACTION:", action)
    print("REMARKS:", remarks)

    institution_user = request.user.institution_profile

    # ==============================
    # REVIEWER
    # ==============================

    if institution_user.role == "reviewer":

        if action == "forward_for_approval":

            if tender.status != "pending_review":
                messages.error(
                    request,
                    "This tender is not pending review."
                )
                return redirect(
                    "tenders:tender_detail",
                    tender_id=tender.id
                )

            tender.status = "pending_approval"
            tender.remarks = ""
            tender.save()

            TenderActivity.objects.create(
                tender=tender,
                performed_by=institution_user,
                action="Forwarded for approval",
                remarks=""
            )

            messages.success(
                request,
                "Tender forwarded for approval successfully."
            )

            return redirect(
                "tenders:tender_detail",
                tender_id=tender.id
            )

        # ==============================
        # REVIEWER REJECT
        # ==============================

        elif action == "reject":

            if tender.status != "pending_review":
                messages.error(
                    request,
                    "This tender cannot be rejected from its current status."
                )

                return redirect(
                    "tenders:tender_detail",
                    tender_id=tender.id
                )

            if not remarks:
                messages.error(
                    request,
                    "Rejection remarks are required."
                )

                return redirect(
                    "tenders:tender_detail",
                    tender_id=tender.id
                )

            # CHANGE STATUS
            tender.status = "rejected"

            # SAVE REMARKS
            tender.remarks = remarks

            # SAVE DATABASE
            tender.save(
                update_fields=[
                    "status",
                    "remarks",
                    "updated_at"
                ]
            )

            # CREATE ACTIVITY LOG
            TenderActivity.objects.create(
                tender=tender,
                performed_by=institution_user,
                action="Rejected tender",
                remarks=remarks
            )

            messages.success(
                request,
                "Tender rejected successfully."
            )

            return redirect(
                "tenders:tender_detail",
                tender_id=tender.id
            )

    # ==============================
    # ADMIN
    # ==============================

    if institution_user.role == "admin":

        if action == "publish":

            if tender.status != "pending_approval":
                messages.error(
                    request,
                    "This tender is not pending approval."
                )

                return redirect(
                    "tenders:tender_detail",
                    tender_id=tender.id
                )

            tender.status = "published"
            tender.remarks = ""
            tender.save()

            TenderActivity.objects.create(
                tender=tender,
                performed_by=institution_user,
                action="Published tender",
                remarks=""
            )

            messages.success(
                request,
                "Tender published successfully."
            )

            return redirect(
                "tenders:tender_detail",
                tender_id=tender.id
            )

        elif action == "reject":

            if tender.status != "pending_approval":
                messages.error(
                    request,
                    "This tender is not pending approval."
                )

                return redirect(
                    "tenders:tender_detail",
                    tender_id=tender.id
                )

            if not remarks:
                messages.error(
                    request,
                    "Rejection remarks are required."
                )

                return redirect(
                    "tenders:tender_detail",
                    tender_id=tender.id
                )

            tender.status = "rejected"
            tender.remarks = remarks

            tender.save(
                update_fields=[
                    "status",
                    "remarks",
                    "updated_at"
                ]
            )

            TenderActivity.objects.create(
                tender=tender,
                performed_by=institution_user,
                action="Rejected tender",
                remarks=remarks
            )

            messages.success(
                request,
                "Tender rejected successfully."
            )

            return redirect(
                "tenders:tender_detail",
                tender_id=tender.id
            )

    messages.error(
        request,
        "Invalid action or insufficient permission."
    )

    return redirect(
        "tenders:tender_detail",
        tender_id=tender.id
    )
    
@login_required
@company_login_required
@company_role_required(allowed_roles=['bid_submitter'])
def submit_bid(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id)
    company = get_object_or_404(Company, user=request.user)

    existing_bid = Bid.objects.filter(tender=tender, company=company, status__in=['draft', 'pending_approval']).first()

    if company.verification_status != 'approved':
        messages.error(request, "Your company profile must be verified before you can submit bids. Please complete your verification process.")
        return redirect('company:dashboard')

    now = timezone.now()
    if tender.status != 'published' or (tender.opening_date and now < tender.opening_date) or (tender.deadline and now > tender.deadline):
        messages.error(request, "This tender is not currently open for bidding.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    # If a submitted bid exists (not a draft), prevent new submission
    if Bid.objects.filter(tender=tender, company=company).exclude(status__in=['draft', 'pending_approval']).exists():
        messages.warning(request, "You have already submitted a bid for this tender.")
        return redirect('tenders:tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        # If an existing draft is found, use it as the instance for the form
        form = BidSubmissionForm(request.POST, request.FILES, instance=existing_bid)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.tender = tender
            bid.company = company
            bid.status = 'pending_approval'  # Always save/resave as pending approval
            bid.remarks = None # Clear any previous rejection remarks upon resubmission
            bid.save()
            messages.success(request, "Your bid has been saved as a draft and sent to your company admin for review and final submission.")
            return redirect('tenders:my_bids')
    else: 
        # If an existing draft is found, pre-populate the form with its data
        form = BidSubmissionForm(instance=existing_bid)

    context = {
        'form': form,
        'tender': tender,
        'existing_bid': existing_bid, # Pass existing bid to template for context
        'company': company,
        'role': company.role,
    }
    return render(request, 'tenders/submit_bid.html', context)

@login_required
@company_login_required
@company_role_required(allowed_roles=['admin'])
def review_and_submit_bid(request, bid_id):
    """Allows a company admin to review a draft bid and submit it."""
    bid = get_object_or_404(Bid.objects.select_related('tender', 'company'), pk=bid_id)
    admin_company = get_object_or_404(Company, user=request.user)

    # Security check: ensure the bid belongs to the admin's company and is a draft
    if bid.company.company_name != admin_company.company_name or bid.status != 'pending_approval':
        messages.error(request, "You do not have permission to review this bid or it's not in a reviewable state.")
        return redirect('company:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'submit_bid':
            bid.status = 'submitted'
            bid.submitted_at = timezone.now() # Update submission time to when admin submits
            bid.remarks = "" # Clear any previous rejection remarks
            bid.save()
            messages.success(request, f"The bid for '{bid.tender.title}' has been successfully submitted.")
            return redirect('company:dashboard')

        elif action == 'reject_draft':
            remarks = request.POST.get('remarks', '').strip()
            if not remarks:
                messages.error(request, "Remarks are required to reject a bid.")
                # Re-render the page with the error message and necessary context
                return render(request, 'tenders/review_bid.html', {
                    'bid': bid,
                    'company': admin_company,
                    'role': admin_company.role,
                })
            else:
                # Keep the status as 'pending_approval' so the submitter can edit it.
                bid.remarks = f"Internally rejected by admin. Reason: {remarks}"
                bid.save(update_fields=['remarks'])
                messages.warning(request, f"The draft bid for '{bid.tender.title}' has been returned to the submitter with your remarks.")
                return redirect('company:dashboard')
    
    return render(request, 'tenders/review_bid.html', {
        'bid': bid,
        'company': admin_company,
        'role': admin_company.role,
    })

@login_required
@company_login_required
def my_bids(request):
    """Displays all bids associated with the user's company."""
    company = get_object_or_404(Company, user=request.user)
    # Filter bids by the company name to show all bids for the company, not just the user.
    bids = Bid.objects.filter(company__company_name=company.company_name).select_related('tender', 'tender__institution').order_by('-submitted_at')
    context = {
        'bids': bids,
        'company': company, # Pass company for role checking in template
        'role': company.role, # Pass role for sidebar
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