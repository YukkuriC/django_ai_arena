"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.urls import path, re_path, include
from .helpers import sorry
from django.views.generic.base import RedirectView
from django.conf import settings
from django.views.static import serve

handler404 = sorry
handler500 = sorry


def missing_route(request, route):
    return sorry(request, text=['不存在的地址:', route])


urlpatterns = [
    path(
        'favicon.ico', RedirectView.as_view(url=r'assets/images/favicon.png')),
    path('', include('usr_sys.urls')),
    path('', include('match_sys.urls')),
    path('', include('ajax_sys.urls')),
    path('', include('external.urls')),
    path('1145141919810/', admin.site.urls),
    re_path('(.+)/$', missing_route)
]

if settings.DEBUG:
    urlpatterns.insert(
        0,
        re_path(r'^STORAGE/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    )
