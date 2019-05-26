from django.contrib import admin

# Register your models here.
from . import models
from match_sys.models import Code


class CodeInline(admin.TabularInline):
    model = Code


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    inlines = [CodeInline]
    list_display = [
        'username', 'real_name', 'stu_code', 'nickname', 'email_validated',
        'is_admin'
    ]
    search_fields = ['username', 'real_name', 'stu_code', 'nickname']


from main.helpers import auto_admin
auto_admin(models)