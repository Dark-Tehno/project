"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

from .views import SecureMediaView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('media/<path:file_path>', SecureMediaView.as_view()),

    path('news/', include('news.urls')),
    path('news/api/v1/', include('news.v1.urls')),
    path('account/api/', include('account.urls')),
    path('chat/api/', include('chat.urls')),
    path('DZ/', include('DZ.urls')),
    path('mail/', include('mail.urls')),
    
    path('', include('portfolio.urls')),
    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)