from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.views.static import serve
from ranged_response import RangedFileResponse
import os

def ranged_media_serve(request, path, document_root=None, show_indexes=False):
    response = serve(request, path, document_root, show_indexes)
    if path.endswith(('.mp4', '.webm', '.ogv')):
        file_path = os.path.join(document_root, path)
        return RangedFileResponse(request, open(file_path, 'rb'), content_type='video/mp4')
    return response

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('courses/', include('courses.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
    path('', RedirectView.as_view(url='/users/home/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', ranged_media_serve, {'document_root': settings.MEDIA_ROOT}),
    ]