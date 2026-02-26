from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from attendance.views import AdminLoginView, StaffLoginView

admin.site.site_header = "CampusOne Admin"
admin.site.site_title = "CampusOne Admin Portal"
admin.site.index_title = "CampusOne Management Console"

urlpatterns = [
    path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin/', admin.site.urls),
    path('accounts/login/', StaffLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('attendance.urls')),
    path('food/', include('food.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
