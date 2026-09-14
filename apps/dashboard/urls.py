from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.login_admin, name='login'),
    path('logout/', views.logout_admin, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload-csv/', views.upload_csv, name='upload_csv'),
    path('kelola-saham/', views.kelola_saham, name='kelola_saham'),
    path('kelola-sektor/', views.kelola_sektor, name='kelola_sektor'),
    path('kriteria-pairwise/', views.kriteria_pairwise, name='kriteria_pairwise'),
    path('proses-analisis/', views.proses_analisis, name='proses_analisis'),
    path('hasil-ranking/', views.hasil_ranking_admin, name='hasil_ranking'),
    path('generate-pdf/', views.generate_pdf, name='generate_pdf'),
    path('download-csv/', views.download_csv, name='download_csv'),
    path('riwayat/', views.riwayat_analisis, name='riwayat'),
    path('api-info/', views.api_info, name='api_info'),
]