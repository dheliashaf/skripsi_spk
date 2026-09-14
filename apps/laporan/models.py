from django.db import models
from django.contrib.auth.models import User
from apps.sektor.models import Sektor

class RiwayatAnalisis(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='riwayat_analisis')
    sektor = models.ForeignKey(Sektor, on_delete=models.SET_NULL, null=True, blank=True, related_name='riwayat_analisis')
    periode = models.CharField(max_length=20, blank=True, null=True)
    top_n = models.IntegerField(default=5)
    
    judul = models.CharField(max_length=255, blank=True)
    file_pdf = models.FileField(upload_to='pdf_results/', verbose_name="File PDF")
    data_json = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Riwayat Analisis"
        verbose_name_plural = "Riwayat Analisis"
        ordering = ['-created_at']

    def __str__(self):
        sektor_nama = self.sektor.nama if self.sektor else "Semua Sektor"
        return f"{self.created_at.strftime('%d-%m-%Y %H:%M')} - {sektor_nama}"