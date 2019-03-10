from django.contrib import admin
from django.db.models.base import ModelBase

# Register your models here.
from . import models
from main.helpers import auto_admin
auto_admin(models)