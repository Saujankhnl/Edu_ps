from django.core.exceptions import PermissionDenied
from functools import wraps
from .models import InstitutionUser

def role_required(allowed_roles=[]):
    """
    Decorator for views that checks that the user is logged in and has one of the allowed roles.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # This will be handled by @login_required, but it's good practice
                raise PermissionDenied
            try:
                role = request.user.institution_profile.role
                if role in allowed_roles:
                    return view_func(request, *args, **kwargs)
            except InstitutionUser.DoesNotExist:
                pass # Let the view handle no-profile cases
            raise PermissionDenied
        return _wrapped_view
    return decorator