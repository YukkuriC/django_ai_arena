from django.contrib import admin
from django.db.models.base import ModelBase

# Register your models here.
from . import models


@admin.register(models.Code)
class CodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'author', 'ai_type', 'edit_datetime', 'score']
    list_filter = ['ai_type']
    search_fields = ['name', 'author__username']
    date_hierarchy = 'edit_datetime'


@admin.register(models.PairMatch)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        'ai_type', 'code1', 'code2', 'status', 'run_datetime', 'is_ranked'
    ]
    list_filter = ['ai_type', 'status', 'is_ranked']
    search_fields = [
        'code1__name', 'code2__name', 'code1__author__username',
        'code2__author__username'
    ]
    date_hierarchy = 'run_datetime'
    actions = ['set_stopped']

    def set_stopped(self, request, queryset):
        queryset.filter(status=1).update(status=3)
        self.message_user(request, '已中止')

    set_stopped.short_description = '中止'


from main.helpers import auto_admin
auto_admin(models)