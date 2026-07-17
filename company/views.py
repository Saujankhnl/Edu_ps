from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
 
from .models import Company
from tenders.models import Tender, Bid
from .forms import CompanyProfileForm, PasswordChangeForm

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
    my_bids = Bid.objects.filter(company=company) # All bids by this company
    
    stats = {
        'total_published_tenders': total_published_tenders,
        'total_submitted_bids': my_bids.count(),
        'active_bids': my_bids.filter(status__in=['submitted', 'under_review', 'shortlisted']).count(),
        'successful_bids': my_bids.filter(status='accepted').count(), # New stat for successful bids
        'total_failed_offers': my_bids.filter(status='rejected').count(), # Only rejected bids count as failed
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
def analytics_reports(request):
    """Placeholder view for analytics and reports."""
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
    }
    return render(request, 'company/analytics_reports.html', context)