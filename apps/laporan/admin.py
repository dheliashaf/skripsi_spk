from django.contrib import admin
from .models import RiwayatAnalisis

@admin.register(RiwayatAnalisis)
class RiwayatAnalisisAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'sektor', 'periode', 'created_at']
    list_filter = ['sektor', 'periode']