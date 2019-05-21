from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('home/', views.home),
    path('register/', views.register),
    path('login/', views.login),
    path('logout/', views.logout),
    path('validate/', views.validate),
    path('validate/<str:code>/', views.activate),
    path('changepasswd/', views.changepasswd),
    path('user/<str:userid>/', views.view_user),
    path('settings/', views.user_settings),
    path('forgotpasswd/', views.forgotpasswd),
    path('forgotpasswd/<str:code>/', views.forgotpasswd),
]
