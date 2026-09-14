from django.contrib import admin
from .models import Saham

@admin.register(Saham)
class SahamAdmin(admin.ModelAdmin):
    list_display = ['kode_saham', 'nama_perusahaan', 'sektor', 'periode']
    search_fields = ['kode_saham', 'nama_perusahaan']
    list_filter = ['sektor', 'periode']