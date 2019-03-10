from django.urls import path
from . import views

urlpatterns = [
    path('code/<str:code_id>/', views.view_code),
    path('match/<str:match_name>/', views.view_pairmatch),
    path('match/<str:match_name>/<str:record_id>/', views.view_record),
    path('upload/', views.upload),
    path('lobby/run_match/', views.pairmatch),
    path('lobby/match_invitation/', views.invite_match),
    path('games/', views.game_info),
    path('lobby/', views.lobby),
]
