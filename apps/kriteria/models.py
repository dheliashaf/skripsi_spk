from django.db import models

class Kriteria(models.Model):
    class SifatKriteria(models.TextChoices):
        BENEFIT = 'BENEFIT', 'Benefit'
        COST = 'COST', 'Cost'

    kode = models.CharField(max_length=10, unique=True)
    nama = models.CharField(max_length=100)
    sifat = models.CharField(max_length=10, choices=SifatKriteria.choices, default=SifatKriteria.BENEFIT)
    bobot = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kriteria"
        verbose_name_plural = "Daftar Kriteria"
        ordering = ['kode']

    def __str__(self):
        return f"{self.kode} - {self.nama} ({self.get_sifat_display()})"

    def is_benefit(self):
        return self.sifat == self.SifatKriteria.BENEFIT


class PairwiseComparison(models.Model):
    kriteria_1 = models.ForeignKey(Kriteria, on_delete=models.CASCADE, related_name='pairwise_as_first')
    kriteria_2 = models.ForeignKey(Kriteria, on_delete=models.CASCADE, related_name='pairwise_as_second')
    
    fuzzy_l = models.FloatField(verbose_name="Fuzzy l")
    fuzzy_m = models.FloatField(verbose_name="Fuzzy m")
    fuzzy_u = models.FloatField(verbose_name="Fuzzy u")
    nilai_crisp = models.IntegerField(verbose_name="Nilai Crisp (1-9)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perbandingan Pairwise"
        verbose_name_plural = "Data Perbandingan Pairwise"
        unique_together = ('kriteria_1', 'kriteria_2')

    def __str__(self):
        return f"{self.kriteria_1.kode} vs {self.kriteria_2.kode} = {self.nilai_crisp}"

    def get_fuzzy_tuple(self):
        return (self.fuzzy_l, self.fuzzy_m, self.fuzzy_u)