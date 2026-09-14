from django.db import models

class Sektor(models.Model):
    nama = models.CharField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sektor"
        verbose_name_plural = "Daftar Sektor"
        ordering = ['nama']

    def __str__(self):
        return self.nama