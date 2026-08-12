from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from .models import Company

def company_login_required(view_func):
    """
    Decorator to ensure user is a logged-in company user.
    If not authenticated, redirects to login.
    If authenticated but no company profile, redirects to home with an error.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('accounts:login_page')
        
        if not hasattr(request.user, 'company'):
            messages.error(request, "Your user account is not associated with a company profile.")
            return redirect('accounts:home') # Or a page to create a company profile
        
        return view_func(request, *args, **kwargs)
    return wrapper

def company_role_required(allowed_roles):
    """
    Decorator for company views that checks if the logged-in user has one of the specified roles.
    If not, it sets an error message and redirects to the company dashboard.
    This decorator assumes company_login_required has already run or the user is guaranteed to have a company profile.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # We can assume request.user has a 'company' attribute due to company_login_required
            company_profile = request.user.company
            
            if company_profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f"You do not have the required role ({', '.join(allowed_roles)}) to access this page. Your current role is '{company_profile.get_role_display()}'.")
                return redirect('company:dashboard')
        return wrapper
    return decorator