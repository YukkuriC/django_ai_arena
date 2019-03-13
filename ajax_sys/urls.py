from django.urls import path
from . import tables

urlpatterns = [
    path('table/match/', tables.match_table_content),
    path('table/code/', tables.code_table_content),
]
