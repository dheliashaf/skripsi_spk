from django.urls import path
from . import views

urlpatterns = [
    path('', views.beranda, name='beranda'),
    path('data-saham/', views.data_saham, name='data_saham'),
    path('proses-analisis/', views.proses_analisis, name='proses_analisis'),
    path('hasil-rekomendasi/', views.hasil_rekomendasi, name='hasil_rekomendasi'),
    path('tentang-metode/', views.tentang_metode, name='tentang_metode'),
    path('generate-pdf-user/', views.generate_pdf_user, name='generate_pdf_user'),
]