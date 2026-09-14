from django.db import models
from apps.sektor.models import Sektor

class Saham(models.Model):
    kode_saham = models.CharField(max_length=10)
    nama_perusahaan = models.CharField(max_length=255)
    sektor = models.ForeignKey(Sektor, on_delete=models.CASCADE, related_name='saham_set')
    periode = models.CharField(max_length=20)
    
    roe = models.FloatField(verbose_name="ROE (%)")
    eps = models.FloatField(verbose_name="EPS (Rp)")
    per = models.FloatField(verbose_name="PER (x)")
    der = models.FloatField(verbose_name="DER (x)")
    bi_rate = models.FloatField(null=True, blank=True, verbose_name="BI Rate (%)", help_text="BI Rate (%)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saham"
        verbose_name_plural = "Daftar Saham"
        unique_together = ('kode_saham', 'periode')
        ordering = ['kode_saham']

    def __str__(self):
        return f"{self.kode_saham} - {self.nama_perusahaan} ({self.periode})"