from django.contrib import admin

# Register your models here.
from . import models
from main.helpers import auto_admin
auto_admin(models)