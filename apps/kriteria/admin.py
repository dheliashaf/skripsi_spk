from django.contrib import admin
from .models import Kriteria, PairwiseComparison

@admin.register(Kriteria)
class KriteriaAdmin(admin.ModelAdmin):
    list_display = ['kode', 'nama', 'sifat', 'bobot']
    list_filter = ['sifat']

@admin.register(PairwiseComparison)
class PairwiseComparisonAdmin(admin.ModelAdmin):
    list_display = ['kriteria_1', 'kriteria_2', 'nilai_crisp']