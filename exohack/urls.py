from django.conf import settings
from django.conf.urls.static import static
from hack import views
from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cv-short-list-query/', views.CVShortlisting),
    path('upload-cv/', views.UploadCV),
    re_path(r'^', include('hack.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
