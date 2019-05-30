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
from django.urls import path, include
from .helpers import sorry
from django.views.generic.base import RedirectView

handler404 = sorry
handler500 = sorry

urlpatterns = [
    path(
        'favicon.ico', RedirectView.as_view(url=r'assets/images/favicon.png')),
    path('', include('usr_sys.urls')),
    path('', include('match_sys.urls')),
    path('', include('ajax_sys.urls')),
    path('1145141919810/', admin.site.urls),
]
