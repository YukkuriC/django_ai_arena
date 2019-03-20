from django.urls import path
from . import tables, views

urlpatterns = [
    path('msg/', views.message_update),
    path('table/match/', tables.MatchTablePage),
    path('table/code/', tables.CodeTablePage),
]
