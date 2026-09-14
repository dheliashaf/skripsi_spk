from django.contrib import admin
from .models import Sektor

@admin.register(Sektor)
class SektorAdmin(admin.ModelAdmin):
    list_display = ['nama', 'deskripsi']
    search_fields = ['nama']