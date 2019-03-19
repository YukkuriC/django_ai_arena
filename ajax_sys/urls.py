from django.urls import path
from . import tables, views

urlpatterns = [
    path('msg/', views.message_update),
    path('table/match/', tables.match_table_content),
    path('table/code/', tables.code_table_content),
]
