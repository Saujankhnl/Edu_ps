from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import InstitutionUser, Tender, Institution
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponseForbidden


@login_required
def dashboard(request):
    try:
        institution_user = InstitutionUser.objects.get(user=request.user)
        institution = institution_user.institution
        role = institution_user.role
    except InstitutionUser.DoesNotExist:
        return render(request, 'institution/error_no_profile.html')

    context = {
        'institution_user': institution_user,
        'role': role,
        'stats': {},
        'tenders': []
    }

    if role == 'admin':
        
        context['stats'] = {
            'Total Users': InstitutionUser.objects.filter(institution=institution).count(),
            'Total Tenders': Tender.objects.filter(institution=institution).count(),
            'Pending Approval': Tender.objects.filter(institution=institution, status='pending_approval').count(),
            'Published Tenders': Tender.objects.filter(institution=institution, status='published').count(),
            'Rejected Tenders': Tender.objects.filter(institution=institution, status='rejected').count(),
        }
        # Admin can see all tenders in the institution.
        context['tenders'] = Tender.objects.filter(institution=institution).order_by('-updated_at')
    elif role == 'creator':
        context['stats'] = {
            'Total Tenders Created': Tender.objects.filter(created_by=institution_user).count(),
            'Draft Tenders': Tender.objects.filter(created_by=institution_user, status='draft').count(),
            'Pending Reviews': Tender.objects.filter(created_by=institution_user, status='pending_review').count(),
            'Returned Tenders': Tender.objects.filter(created_by=institution_user, status='rejected').count(),
        }
        context['tenders'] = Tender.objects.filter(created_by=institution_user).order_by('-updated_at')
        
    elif role == 'reviewer':
        context['stats'] = {
            'Tenders Pending Review': Tender.objects.filter(institution=institution, status='pending_review').count(),
            'Reviewed Tenders': Tender.objects.filter(institution=institution, status__in=['pending_approval', 'approved', 'published', 'rejected']).count(), # Simplified logic
        }
        context['tenders'] = Tender.objects.filter(institution=institution, status__in=['pending_review', 'pending_approval', 'approved', 'published', 'rejected']).order_by('-updated_at')

    return render(request, "institution/dashboard.html", context)

@login_required
def manage_users(request):
    try:
        admin_user_profile = InstitutionUser.objects.select_related('institution').get(user=request.user)
    except InstitutionUser.DoesNotExist:
        return HttpResponseForbidden("You do not have a profile associated with any institution.")

    if admin_user_profile.role != 'admin':
        return HttpResponseForbidden("You do not have permission to access this page.")

    institution = admin_user_profile.institution
    users_list = InstitutionUser.objects.filter(institution=institution).select_related('user').order_by('user__first_name', 'user__last_name')

    # Search and Filter
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

    # Stats
    stats = users_list.aggregate(
        total=Count('id'),
        admins=Count('id', filter=Q(role='admin')),
        creators=Count('id', filter=Q(role='creator')),
        reviewers=Count('id', filter=Q(role='reviewer')),
    )

    context = {
        'institution': institution,
        'users': page_obj,
        'stats': stats,
        'role_choices': InstitutionUser.ROLE_CHOICES,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    return render(request, 'institution/manage_users.html', context)