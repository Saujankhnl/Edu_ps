from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError

from .models import Company, Bid
from institution.models import Tender
from .forms import CompanyProfileForm, PasswordChangeForm, BidSubmissionForm

def company_login_required(view_func):
    """Decorator to ensure user is a logged-in company user."""
    @login_required(login_url='accounts:login_page')
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'company'):
            messages.error(request, "You do not have permission to access this page.")
            return redirect('accounts:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@company_login_required
def dashboard(request):
    company = get_object_or_404(Company, user=request.user)
    
    # Stats
    total_published_tenders = Tender.objects.filter(status='published').count()
    my_bids = Bid.objects.filter(company=company)
    
    stats = {
        'total_published_tenders': total_published_tenders,
        'total_submitted_bids': my_bids.count(),
        'active_bids': my_bids.filter(status__in=['submitted', 'under_review', 'shortlisted']).count(),
    }

    # Recent activities (e.g., recent bids)
    recent_activities = my_bids.select_related('tender').order_by('-submitted_at')[:5]

    context = {
        'company': company,
        'stats': stats,
        'recent_activities': recent_activities,
    }
    return render(request, 'company/company_dashboard.html', context)

@company_login_required
def company_profile(request):
    company = get_object_or_404(Company, user=request.user)
    return render(request, 'company/company_profile.html', {'company': company})

@company_login_required
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

    return render(request, 'company/edit_company_profile.html', {'form': form, 'company': company})

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
    return render(request, 'company/change_password.html', {'form': form})

@company_login_required
def list_published_tenders(request):
    search_query = request.GET.get('q', '')
    tenders = Tender.objects.filter(status='published').order_by('-published_at')

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
def tender_detail(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id, status='published')
    company = get_object_or_404(Company, user=request.user)
    
    existing_bid = Bid.objects.filter(tender=tender, company=company).first()
    
    context = {
        'tender': tender,
        'existing_bid': existing_bid,
    }
    return render(request, 'company/tender_detail.html', context)

@company_login_required
def submit_bid(request, tender_id):
    tender = get_object_or_404(Tender, pk=tender_id, status='published')
    company = get_object_or_404(Company, user=request.user)

    if Bid.objects.filter(tender=tender, company=company).exists():
        messages.error(request, "You have already submitted a bid for this tender.")
        return redirect('company:tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        form = BidSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                bid = form.save(commit=False)
                bid.tender = tender
                bid.company = company
                bid.save()
                messages.success(request, "Your bid has been submitted successfully.")
                return redirect('company:my_bids')
            except IntegrityError:
                messages.error(request, "An error occurred. It's possible you've already bid on this tender.")
                return redirect('company:tender_detail', tender_id=tender.id)
    else:
        form = BidSubmissionForm()

    context = {
        'form': form,
        'tender': tender,
    }
    return render(request, 'company/submit_bid.html', context)

@company_login_required
def my_bids(request):
    company = get_object_or_404(Company, user=request.user)
    bids = Bid.objects.filter(company=company).select_related('tender').order_by('-submitted_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        bids = bids.filter(status=status_filter)

    context = {
        'bids': bids,
        'status_choices': Bid.STATUS_CHOICES,
        'status_filter': status_filter,
    }
    return render(request, 'company/my_bids.html', context)

@company_login_required
def bid_detail(request, bid_id):
    company = get_object_or_404(Company, user=request.user)
    bid = get_object_or_404(Bid, pk=bid_id, company=company)
    context = {
        'bid': bid
    }
    return render(request, 'company/bid_detail.html', context)

@company_login_required
def analytics_reports(request):
    """Placeholder view for analytics and reports."""
    return render(request, 'company/analytics_reports.html')