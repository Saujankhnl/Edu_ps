
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("",include("accounts.urls")),
    path("institution/",include("institution.urls")),
    path("company/",include("company.urls")),
    path("tenders/",include("tenders.urls")),
    path("system-admin/",include("system_admin.urls")),

]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)