from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.template.loader import get_template
from django.db import transaction
from io import BytesIO
from xhtml2pdf import pisa
from institution.models import Institution, InstitutionUser
from company.models import Company
from tenders.models import Tender, Bid
from tenders.models import TenderActivity
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
from .forms import AdminProfileForm, AdminPasswordChangeForm
from django.utils import timezone

def is_superuser(user):
    """Check if the user is a superuser."""
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superuser, login_url='/login/')
def dashboard(request):
    """
    Displays a dashboard for the system administrator with system-wide statistics.
    """
    stats = {
        'total_institutions': Institution.objects.filter(is_approved=True).count(),
        'total_companies': Company.objects.filter(is_approved=True).count(),
        'total_tenders': Tender.objects.count(),
        'total_users': User.objects.count(),
    }

    context = {
        'stats': stats,
        'recent_users': User.objects.order_by('-date_joined')[:5],
        'recent_tenders': Tender.objects.order_by('-created_at')[:5],
    }
    return render(request, 'system_admin/dashboard.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def list_pending_institutions(request):
    """Lists all institutions pending approval."""
    # This list should show institutions that are not yet approved and have not been rejected.
    # This includes those who haven't submitted verification ('not_submitted') and those who have ('pending').
    pending_list = Institution.objects.filter(is_approved=False, verification_status__in=['pending', 'not_submitted']).order_by('institution_name')
    
    paginator = Paginator(pending_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'institutions': page_obj,
        'page_title': 'Pending Institutions',
        'page_description': 'Review and approve new institution registrations.'
    }
    return render(request, 'system_admin/institution_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def list_all_institutions(request):
    """Lists all approved institutions."""
    approved_list = Institution.objects.filter(is_approved=True).order_by('-id')
    paginator = Paginator(approved_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'institutions': page_obj,
        'page_title': 'All Approved Institutions',
        'page_description': 'A list of all active institutions on the platform.'
    }
    return render(request, 'system_admin/institution_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def approve_institution(request, institution_id):
    """Approves an institution registration."""
    if request.method == 'POST':
        institution = get_object_or_404(Institution, id=institution_id)
        with transaction.atomic():
            institution.is_approved = True
            # The verification status should be 'approved' when the institution is approved.
            institution.verification_status = 'approved'
            institution.save()

            # Correctly find and activate the admin user for this institution
            try:
                admin_user_profile = InstitutionUser.objects.get(institution=institution, role='admin')
                admin_user_profile.user.is_active = True
                admin_user_profile.user.save()
            except InstitutionUser.DoesNotExist:
                messages.warning(request, f"Institution '{institution.institution_name}' was approved, but no admin user was found to activate.")

            messages.success(request, f"Institution '{institution.institution_name}' has been approved.")
            return redirect('system_admin:pending_institutions')
    else:
        # Redirect if accessed via GET
        return redirect('system_admin:dashboard')

@user_passes_test(is_superuser, login_url='/login/')
def reject_institution(request, institution_id):
    """
    Initiates the rejection process by redirecting to the detail page for remarks.
    This is triggered from the list view.
    """
    if request.method == 'POST':
        institution = get_object_or_404(Institution, id=institution_id)
        # This view's purpose is to lead to the page where remarks can be added.
        messages.info(request, f"Please provide remarks to complete the rejection for '{institution.institution_name}'.")
        return redirect('system_admin:process_verification', institution_id=institution.id)
    else:
        # Redirect if accessed via GET
        return redirect('system_admin:pending_institutions')

@user_passes_test(is_superuser, login_url='/login/')
def list_pending_verifications(request):
    """Lists all institutions with 'pending' verification status."""
    pending_list = Institution.objects.filter(verification_status='pending').order_by('id')
    
    paginator = Paginator(pending_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'institutions': page_obj,
        'page_title': 'Pending Verifications',
        'page_description': 'Review and process new institution verification requests.'
    }
    return render(request, 'system_admin/verification_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def process_verification(request, institution_id):
    """
    Approve or reject an institution's verification submission.
    """
    institution = get_object_or_404(Institution, id=institution_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')

        if action == 'approve':
            with transaction.atomic():
                institution.verification_status = 'approved'
                institution.is_approved = True
                institution.verification_remarks = ''  # Clear remarks on approval
                institution.save()

                try:
                    admin_institution_user = InstitutionUser.objects.get(institution=institution, role='admin')
                    admin_institution_user.user.is_active = True
                    admin_institution_user.user.save()
                except InstitutionUser.DoesNotExist:
                    messages.warning(request, f"Could not find an admin user for '{institution.institution_name}' to activate.")
            messages.success(request, f"'{institution.institution_name}' has been successfully verified and approved.")
            return redirect('system_admin:dashboard')
        
        elif action == 'reject':
            if not remarks:
                messages.error(request, "Remarks are required to reject a verification.")
                return render(request, 'system_admin/verification_detail.html', {'institution': institution})
            with transaction.atomic():
                institution.verification_status = 'rejected'
                institution.is_approved = False # Explicitly set to False on rejection
                institution.verification_remarks = remarks
                institution.save()
            messages.warning(request, f"'{institution.institution_name}' verification has been rejected with remarks.")
            return redirect('system_admin:all_institutions')

    # If not POST, just show the detail for review
    return render(request, 'system_admin/verification_detail.html', {'institution': institution})

@user_passes_test(is_superuser, login_url='/login/')
def tender_monitoring(request):
    """Displays a monitoring page for all tenders in the system."""
    now = timezone.now()
    
    # Fetch all tenders and categorize them
    all_tenders = Tender.objects.select_related('institution').order_by('-created_at')

    # Categorization
    upcoming_tenders = all_tenders.filter(status='published', opening_date__gt=now)
    active_tenders = all_tenders.filter(
        Q(status='published') & 
        (Q(opening_date__isnull=True) | Q(opening_date__lte=now)) &
        (Q(deadline__isnull=True) | Q(deadline__gt=now))
    )
    expired_tenders = all_tenders.filter(Q(status='expired') | Q(deadline__lt=now) & Q(status='published'))
    other_tenders = all_tenders.exclude(
        id__in=upcoming_tenders.values_list('id', flat=True)
    ).exclude(
        id__in=active_tenders.values_list('id', flat=True)
    ).exclude(
        id__in=expired_tenders.values_list('id', flat=True)
    )

    tender_categories = [
        {
            'title': 'Active Tenders',
            'tenders': active_tenders,
            'color_class': 'bg-emerald-500',
        },
        {
            'title': 'Upcoming Tenders',
            'tenders': upcoming_tenders,
            'color_class': 'bg-blue-500',
        },
        {
            'title': 'Expired Tenders',
            'tenders': expired_tenders,
            'color_class': 'bg-slate-500',
        },
        {
            'title': 'Other Statuses',
            'tenders': other_tenders,
            'color_class': 'bg-amber-500',
        }
    ]
    context = {
        'page_title': 'Tender Monitoring',
        'page_description': 'Oversee all tenders across the platform, categorized by their current status.',
        'tender_categories': tender_categories,
    }
    return render(request, 'system_admin/tender_monitoring.html', context)

def render_to_pdf(template_src, context_dict={}):
    """Helper function to render a Django template to a PDF."""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

@user_passes_test(is_superuser, login_url='/login/')
def generate_tender_monitoring_pdf(request):
    """Generates a PDF report for all tenders."""
    now = timezone.now()
    all_tenders = Tender.objects.select_related('institution').order_by('institution__institution_name', '-created_at')

    active_tenders = all_tenders.filter(
            Q(status='published') & 
            (Q(opening_date__isnull=True) | Q(opening_date__lte=now)) &
            (Q(deadline__isnull=True) | Q(deadline__gt=now))
        )
    upcoming_tenders = all_tenders.filter(status='published', opening_date__gt=now)
    expired_tenders = all_tenders.filter(Q(status='expired') | Q(deadline__lt=now) & Q(status='published'))

    pdf_categories = [
        {
            'title': 'Active Tenders',
            'tenders': active_tenders,
        },
        {
            'title': 'Upcoming Tenders',
            'tenders': upcoming_tenders,
        },
        {
            'title': 'Expired Tenders',
            'tenders': expired_tenders,
        },
    ]
    context = {
        'pdf_categories': pdf_categories,
        'report_date': now,
    }

    pdf = render_to_pdf('system_admin/tender_monitoring_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Tender_Monitoring_Report_{now.strftime('%Y-%m-%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    messages.error(request, "There was an error generating the PDF report.")
    return redirect('system_admin:tender_monitoring')

@user_passes_test(is_superuser, login_url='/login/')
def bid_monitoring(request):
    """Displays a monitoring page for all bids in the system."""
    all_bids = Bid.objects.select_related('tender', 'company', 'tender__institution').order_by('-submitted_at')

    # Categorization by status
    bid_categories = []
    # Define a specific order for statuses
    status_order = ['submitted', 'under_review', 'shortlisted', 'accepted', 'rejected']
    
    for status_key in status_order:
        status_display = dict(Bid.STATUS_CHOICES).get(status_key)
        if status_display:
            bids_in_category = all_bids.filter(status=status_key)
            bid_categories.append({
                'title': status_display,
                'bids': bids_in_category,
            })

    context = {
        'page_title': 'Bid Monitoring',
        'page_description': 'Oversee all bids submitted across the platform, categorized by status.',
        'bid_categories': bid_categories,
    }
    return render(request, 'system_admin/bid_monitoring.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def generate_bid_monitoring_pdf(request):
    """Generates a PDF report for all bids."""
    now = timezone.now()
    all_bids = Bid.objects.select_related('tender', 'company', 'tender__institution').order_by('tender__institution__institution_name', 'tender__title', 'submitted_at')

    context = {
        'all_bids': all_bids,
        'report_date': now,
    }

    pdf = render_to_pdf('system_admin/bid_monitoring_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Bid_Monitoring_Report_{now.strftime('%Y-%m-%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    messages.error(request, "There was an error generating the PDF report.")
    return redirect('system_admin:bid_monitoring')

@user_passes_test(is_superuser, login_url='/login/')
def analytics_reports(request):
    """Displays a page with system-wide analytics and charts."""
    # --- KPIs ---
    stats = { # Only count approved entities for these KPIs
        'total_institutions': Institution.objects.filter(is_approved=True).count(),
        'total_companies': Company.objects.filter(is_approved=True).count(),
        'total_users': User.objects.count(),
        'total_tenders': Tender.objects.count(),
        'total_bids': Bid.objects.count(), # All bids, regardless of company approval
    }

    # --- Tender Status Chart (Doughnut) ---
    tender_status_data = Tender.objects.values('status').annotate(count=Count('id')).order_by('-count')
    tender_status_labels = [dict(Tender.STATUS_CHOICES).get(item['status'], 'Unknown') for item in tender_status_data]
    tender_status_counts = [item['count'] for item in tender_status_data]

    # --- Monthly Tender Trend (Line Chart) ---
    tender_trend = (
        Tender.objects.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    tender_trend_labels = [t['month'].strftime('%b %Y') for t in tender_trend]
    tender_trend_counts = [t['count'] for t in tender_trend]

    # --- Monthly Bid Trend (Line Chart) ---
    bid_trend = (
        Bid.objects.annotate(month=TruncMonth('submitted_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    bid_trend_labels = [b['month'].strftime('%b %Y') for b in bid_trend]
    bid_trend_counts = [b['count'] for b in bid_trend]

    # --- Top Lists ---
    top_institutions = Institution.objects.annotate(tender_count=Count('tenders')).order_by('-tender_count')[:5]
    top_companies = Company.objects.annotate(bid_count=Count('bids')).order_by('-bid_count')[:5]

    # --- Quick Insights ---
    insights = {
        'avg_bids_per_tender': round(stats['total_bids'] / stats['total_tenders'], 1) if stats['total_tenders'] > 0 else 0,
        'most_bids_tender': Tender.objects.annotate(num_bids=Count('bids')).order_by('-num_bids').first(),
    }

    # --- Recent Activities ---
    recent_activities = TenderActivity.objects.select_related('tender', 'performed_by__user').order_by('-timestamp')[:7]

    kpi_cards = [
        {
            'label': 'Verified Institutions',
            'value': stats['total_institutions'],
            'icon_path': 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
        },
        {
            'label': 'Verified Companies',
            'value': stats['total_companies'],
            'icon_path': 'M21 13V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6m18 0v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6m18 0H3'
        },
        {
            'label': 'Total Users',
            'value': stats['total_users'],
            'icon_path': 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z'
        },
        {
            'label': 'Total Tenders',
            'value': stats['total_tenders'],
            'icon_path': 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
        },
        {
            'label': 'Total Bids',
            'value': stats['total_bids'],
            'icon_path': 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
        }
    ]

    context = {
        'page_title': 'Analytics & Reports',
        'page_description': 'A comprehensive overview of platform activity and key performance indicators.',
        'stats': stats,
        'chart_data': {
            'tender_status_labels': tender_status_labels,
            'tender_status_counts': tender_status_counts,
            'tender_trend_labels': tender_trend_labels,
            'tender_trend_counts': tender_trend_counts,
            'bid_trend_labels': bid_trend_labels,
            'bid_trend_counts': bid_trend_counts,
        },
        'top_institutions': top_institutions,
        'top_companies': top_companies,
        'insights': insights,
        'recent_activities': recent_activities,
        'kpi_cards': kpi_cards,
    }
    return render(request, 'system_admin/analytics_reports.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def generate_analytics_pdf(request):
    """Generates a PDF summary of the analytics and reports page."""
    now = timezone.now()
    
    # --- KPIs ---
    stats = {
        'total_institutions': Institution.objects.filter(is_approved=True).count(),
        'total_companies': Company.objects.filter(is_approved=True).count(),
        'total_users': User.objects.count(),
        'total_tenders': Tender.objects.count(),
        'total_bids': Bid.objects.count(),
    }

    # --- Tender Status Data ---
    tender_status_data = Tender.objects.values('status').annotate(count=Count('id')).order_by('-count')
    for item in tender_status_data:
        item['status_display'] = dict(Tender.STATUS_CHOICES).get(item['status'], 'Unknown')

    # --- Top Lists ---
    top_institutions = Institution.objects.annotate(tender_count=Count('tenders')).order_by('-tender_count')[:10]
    top_companies = Company.objects.annotate(bid_count=Count('bids')).order_by('-bid_count')[:10]

    context = {
        'report_date': now,
        'stats': stats,
        'tender_status_data': tender_status_data,
        'top_institutions': top_institutions,
        'top_companies': top_companies,
    }

    pdf = render_to_pdf('system_admin/analytics_reports_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Analytics_Report_{now.strftime('%Y-%m-%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    messages.error(request, "There was an error generating the PDF report.")
    return redirect('system_admin:analytics_reports')

@user_passes_test(is_superuser, login_url='/login/')
def view_profile(request):
    """Displays the system administrator's profile."""
    context = {
        'page_title': 'My Profile',
        'page_description': 'View and manage your administrator account details.'
    }
    return render(request, 'system_admin/profile.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def edit_profile(request):
    """Allows the system administrator to edit their profile."""
    user = request.user
    if request.method == 'POST':
        form = AdminProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('system_admin:view_profile')
    else:
        form = AdminProfileForm(instance=user)
    
    context = {
        'form': form,
        'page_title': 'Edit Profile',
        'page_description': 'Update your personal and account information.'
    }
    return render(request, 'system_admin/edit_profile.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def change_password(request):
    """Allows the system administrator to change their password."""
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('system_admin:view_profile')
    else:
        form = AdminPasswordChangeForm(user=request.user)
    
    return render(request, 'system_admin/change_password.html', {'form': form})

@user_passes_test(is_superuser, login_url='/login/')
def manage_all_users(request):
    """Lists all institution users across all institutions for the system admin."""
    # Use select_related to optimize database queries by fetching related user and institution data in a single query.
    users_list = InstitutionUser.objects.select_related('user', 'institution').order_by('institution__institution_name', 'user__username')

    paginator = Paginator(users_list, 15)  # Show 15 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'institution_users': page_obj,
        'page_title': 'User Management',
        'page_description': 'A list of all administrative, creator, and reviewer users across all institutions.'
    }
    return render(request, 'system_admin/user_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def list_pending_companies(request):
    """Lists all companies pending approval."""
    # This list should show companies that are not yet approved and have not been rejected.
    pending_list = Company.objects.filter(is_approved=False, verification_status__in=['pending', 'not_submitted']).order_by('user__date_joined')
    paginator = Paginator(pending_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'companies': page_obj,
        'page_title': 'Pending Companies',
        'page_description': 'Review and approve new company registrations.'
    }
    return render(request, 'system_admin/company_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def list_all_companies(request):
    """Lists all approved companies."""
    approved_list = Company.objects.filter(is_approved=True).order_by('-user__date_joined')
    paginator = Paginator(approved_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'companies': page_obj,
        'page_title': 'All Approved Companies',
        'page_description': 'A list of all active companies on the platform.'
    }
    return render(request, 'system_admin/company_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def approve_company(request, company_id):
    """Approves a company registration."""
    if request.method == 'POST':
        company = get_object_or_404(Company, id=company_id)
        company.is_approved = True
        company.verification_status = 'approved' # Synchronize verification status
        company.user.is_active = True # Also activate the associated user
        company.user.save() # Persist the change to the user's active status
        company.save()
        messages.success(request, f"Company '{company.company_name}' has been approved.")
        return redirect('system_admin:pending_companies')
    else:
        # Redirect if accessed via GET
        return redirect('system_admin:dashboard')

@user_passes_test(is_superuser, login_url='/login/')
def reject_company(request, company_id):
    """
    Initiates the rejection process for a company by redirecting to the detail page for remarks.
    """
    if request.method == 'POST':
        company = get_object_or_404(Company, id=company_id)
        # This view's purpose is to lead to the page where remarks can be added.
        messages.info(request, f"Please provide remarks to complete the rejection for '{company.company_name}'.")
        return redirect('system_admin:process_company_verification', company_id=company.id)
    else:
        # Redirect if accessed via GET
        return redirect('system_admin:pending_companies')


@user_passes_test(is_superuser, login_url='/login/')
def list_pending_company_verifications(request):
    """Lists all companies with 'pending' verification status."""
    pending_list = Company.objects.filter(verification_status='pending').order_by('user__date_joined')
    
    paginator = Paginator(pending_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'companies': page_obj,
        'page_title': 'Pending Company Verifications',
        'page_description': 'Review and process new company verification requests.'
    }
    return render(request, 'system_admin/company_verification_list.html', context)

@user_passes_test(is_superuser, login_url='/login/')
def process_company_verification(request, company_id):
    """
    Approve or reject a company's verification submission.
    """
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')

        if action == 'approve':
            with transaction.atomic():
                company.verification_status = 'approved'
                company.is_approved = True
                company.verification_remarks = ''  # Clear remarks on approval
                company.user.is_active = True
                company.save()
                company.user.save()
            messages.success(request, f"Company '{company.company_name}' has been successfully verified and approved.")
            return redirect('system_admin:dashboard')

        elif action == 'reject':
            if not remarks:
                messages.error(request, "Remarks are required to reject a verification.")
                return render(request, 'system_admin/company_verification_detail.html', {'company': company})
            with transaction.atomic():
                company.verification_status = 'rejected'
                company.verification_remarks = remarks
                company.save()
            messages.warning(request, f"Company '{company.company_name}' verification has been rejected with remarks.")
            return redirect('system_admin:dashboard')

    # If not POST, just show the detail for review
    return render(request, 'system_admin/company_verification_detail.html', {'company': company})