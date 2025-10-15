"""
URL configuration for mmg_backend_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django_encrypted_filefield.views import FetchView
from django_encrypted_filefield.constants import FETCH_URL_NAME
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView, TokenRefreshView

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='root-redirect'),
    path('admin/', admin.site.urls),
    path('encrypted-media<path:path>/', FetchView.as_view(), name=FETCH_URL_NAME),
    path('api/finance/', include('finance.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/project/', include('project.urls')),
    path('api/team/', include('team.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
