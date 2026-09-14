from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import pandas as pd
import io
import json

from apps.saham.models import Saham
from apps.sektor.models import Sektor
from apps.kriteria.models import Kriteria, PairwiseComparison
from apps.laporan.models import RiwayatAnalisis
from apps.kriteria.services.fuzzy_ahp_service import FuzzyAHPService


def login_admin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard:dashboard')
        else:
            return render(request, 'dashboard/login.html', {'error': 'Username atau password salah'})
    return render(request, 'dashboard/login.html')


@login_required(login_url='dashboard:login')
def dashboard(request):
    ranking_terbaru = request.session.get('hasil_ranking', [])
    ranking_top5 = ranking_terbaru[:5] if ranking_terbaru else []
    
    context = {
        'total_saham': Saham.objects.count(),
        'total_sektor': Sektor.objects.count(),
        'total_riwayat': RiwayatAnalisis.objects.count(),
        'ranking_terbaru': ranking_top5,
        'active': 'dashboard'
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required(login_url='dashboard:login')
def upload_csv(request):
    context = {
        'total_saham': Saham.objects.count(),
        'total_sektor': Sektor.objects.count(),
        'active': 'upload'
    }

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            context['error'] = 'File harus berformat CSV!'
            return render(request, 'dashboard/upload_csv.html', context)

        try:
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))
            required_cols = ['kode_saham', 'nama_perusahaan', 'sektor', 'periode', 'roe', 'eps', 'per', 'der', 'bi_rate']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                context['error'] = f'Kolom tidak ditemukan: {missing}'
                return render(request, 'dashboard/upload_csv.html', context)

            df.columns = df.columns.str.strip()
            numeric_cols = ['roe', 'eps', 'per', 'der', 'bi_rate']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['roe', 'eps', 'per', 'der'])

            if df.empty:
                context['error'] = 'Tidak ada data valid dalam file CSV!'
                return render(request, 'dashboard/upload_csv.html', context)

            saved_count = 0
            for _, row in df.iterrows():
                sektor_obj, _ = Sektor.objects.get_or_create(nama=row['sektor'].strip())
                Saham.objects.update_or_create(
                    kode_saham=row['kode_saham'].strip(),
                    periode=row['periode'].strip(),
                    defaults={
                        'nama_perusahaan': row['nama_perusahaan'].strip(),
                        'sektor': sektor_obj,
                        'roe': float(row['roe']),
                        'eps': float(row['eps']),
                        'per': float(row['per']),
                        'der': float(row['der']),
                        'bi_rate': float(row['bi_rate']) if pd.notna(row['bi_rate']) else None,
                    }
                )
                saved_count += 1

            context['total_saham'] = Saham.objects.count()
            context['total_sektor'] = Sektor.objects.count()
            context['success'] = f'Berhasil import {saved_count} data saham!'

        except Exception as e:
            context['error'] = f'Terjadi kesalahan: {str(e)}'

    return render(request, 'dashboard/upload_csv.html', context)


@login_required(login_url='dashboard:login')
def kelola_saham(request):
    saham_list = Saham.objects.all().select_related('sektor')
    return render(request, 'dashboard/kelola_saham.html', {
        'saham_list': saham_list,
        'active': 'saham'
    })


@login_required(login_url='dashboard:login')
def kelola_sektor(request):
    sektor_list = Sektor.objects.all()
    return render(request, 'dashboard/kelola_sektor.html', {
        'sektor_list': sektor_list,
        'active': 'sektor'
    })


@login_required(login_url='dashboard:login')
def kriteria_pairwise(request):
    kriteria_list = Kriteria.objects.all().order_by('kode')
    pairwise_list = PairwiseComparison.objects.all()

    success_message = None
    error_message = None
    bobot_result = None

    # Ambil nilai pairwise yang sudah tersimpan untuk ditampilkan di form
    pairwise_values = {}
    for p in pairwise_list:
        key = f"{p.kriteria_1.kode.lower()}_{p.kriteria_2.kode.lower()}"
        pairwise_values[key] = p.nilai_crisp

    print("=" * 60)
    print("PAIRWISE VALUES (SEBELUM POST):")
    for k, v in pairwise_values.items():
        print(f"  {k}: {v}")
    print("=" * 60)

    if request.method == 'POST':
        if 'simpan_pairwise' in request.POST:
            # ============================================================
            # NILAI PAIRWISE — MATCH DENGAN TEMPLATE
            # ============================================================
            nilai_pairwise = {
                'roe_eps': request.POST.get('roe_eps'),
                'roe_per': request.POST.get('roe_per'),
                'roe_der': request.POST.get('roe_der'),
                'roe_bi_rate': request.POST.get('roe_bi_rate'),
                'eps_per': request.POST.get('eps_per'),
                'eps_der': request.POST.get('eps_der'),
                'eps_bi_rate': request.POST.get('eps_bi_rate'),
                'per_der': request.POST.get('per_der'),
                'per_bi_rate': request.POST.get('per_bi_rate'),
                'der_bi_rate': request.POST.get('der_bi_rate'),
            }

            print("RAW POST VALUES:")
            for k, v in nilai_pairwise.items():
                print(f"  {k}: {v}")

            # ============================================================
            # KONVERSI KE FLOAT — DENGAN DUKUNGAN KOMA
            # ============================================================
            for key in nilai_pairwise:
                if nilai_pairwise[key] is None or nilai_pairwise[key] == '':
                    error_message = f"Nilai untuk {key} kosong! Harus diisi."
                    print(f"❌ {error_message}")
                    return render(request, 'dashboard/kriteria_pairwise.html', {
                        'kriteria_list': kriteria_list,
                        'pairwise_list': pairwise_list,
                        'bobot_result': bobot_result,
                        'pairwise_values': pairwise_values,
                        'error': error_message,
                        'active': 'kriteria'
                    })
                try:
                    # Ganti koma dengan titik untuk format Indonesia
                    val = nilai_pairwise[key].replace(',', '.')
                    nilai_pairwise[key] = float(val)
                except ValueError:
                    error_message = f"Nilai untuk {key} harus berupa angka!"
                    print(f"❌ {error_message}")
                    return render(request, 'dashboard/kriteria_pairwise.html', {
                        'kriteria_list': kriteria_list,
                        'pairwise_list': pairwise_list,
                        'bobot_result': bobot_result,
                        'pairwise_values': pairwise_values,
                        'error': error_message,
                        'active': 'kriteria'
                    })

            print("AFTER CONVERSION (dengan koma diganti titik):")
            for k, v in nilai_pairwise.items():
                print(f"  {k}: {v}")

            mapping = {
                'roe_eps': ('ROE', 'EPS'),
                'roe_per': ('ROE', 'PER'),
                'roe_der': ('ROE', 'DER'),
                'roe_bi_rate': ('ROE', 'BI_RATE'),
                'eps_per': ('EPS', 'PER'),
                'eps_der': ('EPS', 'DER'),
                'eps_bi_rate': ('EPS', 'BI_RATE'),
                'per_der': ('PER', 'DER'),
                'per_bi_rate': ('PER', 'BI_RATE'),
                'der_bi_rate': ('DER', 'BI_RATE'),
            }

            try:
                for key, (kode1, kode2) in mapping.items():
                    val = nilai_pairwise[key]
                    if val <= 0:
                        raise ValueError(f"Nilai untuk {kode1} vs {kode2} harus lebih dari 0 (saat ini {val})")
                    k1 = Kriteria.objects.get(kode=kode1)
                    k2 = Kriteria.objects.get(kode=kode2)
                    PairwiseComparison.objects.filter(kriteria_1=k1, kriteria_2=k2).delete()
                    fuzzy_l, fuzzy_m, fuzzy_u = FuzzyAHPService.get_fuzzy_value(val)
                    PairwiseComparison.objects.create(
                        kriteria_1=k1,
                        kriteria_2=k2,
                        fuzzy_l=fuzzy_l,
                        fuzzy_m=fuzzy_m,
                        fuzzy_u=fuzzy_u,
                        nilai_crisp=val
                    )

                success_message = "Data pairwise berhasil disimpan!"

                # Refresh pairwise_values setelah simpan
                pairwise_values = {}
                for p in PairwiseComparison.objects.all():
                    key = f"{p.kriteria_1.kode.lower()}_{p.kriteria_2.kode.lower()}"
                    pairwise_values[key] = p.nilai_crisp

                print("PAIRWISE VALUES SETELAH SIMPAN:")
                for k, v in pairwise_values.items():
                    print(f"  {k}: {v}")
                print("=" * 60)

            except Exception as e:
                error_message = f"Gagal menyimpan pairwise: {str(e)}"
                print("❌ ERROR SAVE:", str(e))

        elif 'hitung_bobot' in request.POST:
            try:
                result = FuzzyAHPService.calculate_weights()
                bobot_result = result['weights']
                cr_value = result['cr']
                is_consistent = result['is_consistent']
                if is_consistent:
                    success_message = f"✅ Bobot berhasil dihitung! CR = {cr_value:.4f} (Valid, < 0.1)"
                else:
                    error_message = f"❌ CR = {cr_value:.4f} ≥ 0.1 (Tidak konsisten, ulangi input pairwise)"
                kriteria_list = Kriteria.objects.all().order_by('kode')
            except Exception as e:
                error_message = f"Error menghitung bobot Fuzzy AHP: {str(e)}"
                print("❌ ERROR HITUNG BOBOT:", str(e))

    context = {
        'kriteria_list': kriteria_list,
        'pairwise_list': pairwise_list,
        'bobot_result': bobot_result,
        'pairwise_values': pairwise_values,
        'success': success_message,
        'error': error_message,
        'active': 'kriteria'
    }
    return render(request, 'dashboard/kriteria_pairwise.html', context)


@login_required(login_url='dashboard:login')
def proses_analisis(request):
    total_saham = Saham.objects.count()
    total_sektor = Sektor.objects.count()
    sektor_list = Sektor.objects.all()
    bobot_tersedia = Kriteria.objects.filter(bobot__gt=0).exists()

    log_proses = []
    hasil_ranking = False
    error_message = None

    if request.method == 'POST':
        if 'jalankan_analisis' in request.POST:
            sektor_id = request.POST.get('sektor')
            periode = request.POST.get('periode', 'Q4-2025')
            top_n = request.POST.get('top', '5')

            if sektor_id == '':
                sektor_id = None

            try:
                saham_data = Saham.objects.all().select_related('sektor')
                if sektor_id:
                    saham_data = saham_data.filter(sektor_id=sektor_id)
                if periode:
                    saham_data = saham_data.filter(periode=periode)

                print("=" * 50)
                print("DEBUG PROSES ANALISIS (ADMIN)")
                print(f"Jumlah saham ditemukan: {saham_data.count()}")

                if not saham_data.exists():
                    error_message = "Tidak ada data saham untuk sektor/periode yang dipilih."
                    log_proses = [{'pesan': error_message, 'icon': 'exclamation-circle', 'warna': 'danger'}]
                else:
                    bobot_dict = {k.kode: k.bobot for k in Kriteria.objects.all() if k.bobot > 0}
                    print("Bobot kriteria:", bobot_dict)

                    if not bobot_dict:
                        error_message = "Bobot kriteria belum dihitung. Silakan hitung bobot Fuzzy AHP terlebih dahulu."
                        log_proses = [{'pesan': error_message, 'icon': 'exclamation-circle', 'warna': 'danger'}]
                    else:
                        import pandas as pd
                        data = []
                        for s in saham_data:
                            data.append({
                                'kode_saham': s.kode_saham,
                                'nama_perusahaan': s.nama_perusahaan,
                                'sektor': s.sektor.nama if s.sektor else '',
                                'periode': s.periode,
                                'roe': float(s.roe) if s.roe else 0.0,
                                'eps': float(s.eps) if s.eps else 0.0,
                                'per': float(s.per) if s.per else 0.0,
                                'der': float(s.der) if s.der else 0.0,
                                'bi_rate': float(s.bi_rate) if s.bi_rate else 0.0,  # ← TETAP ADA
                            })
                        df = pd.DataFrame(data)
                        print("DataFrame awal (5 baris pertama):")
                        print(df.head())

                        from apps.analisis.services.normalization import NormalizationService
                        kriteria_sifat = {k.kode: k.sifat for k in Kriteria.objects.all()}
                        df_normalized = df.copy()
                        # ============================================================
                        # PERUBAHAN: HAPUS 'bi_rate' DARI NORMALISASI
                        # ============================================================
                        for col in ['roe', 'eps', 'per', 'der']:  # ← HAPUS 'bi_rate'
                            if col in df.columns:
                                sifat = kriteria_sifat.get(col.upper(), 'BENEFIT')
                                df_normalized[col] = NormalizationService.minmax_normalization(df[col], sifat)

                        print("DataFrame setelah normalisasi (5 baris pertama):")
                        print(df_normalized.head())

                        from apps.analisis.services.ranking import RankingService
                        skor = RankingService.hitung_skor_akhir(df_normalized, bobot_dict)
                        print("Skor mentah:", skor)

                        df_ranked = RankingService.ranking_per_sektor(df_normalized, skor, 'sektor')
                        print("DataFrame ranking (5 baris pertama):")
                        print(df_ranked.head())

                        top_n_int = int(top_n) if top_n.isdigit() else 999
                        df_top = RankingService.top_n_saham(df_ranked, top_n_int)
                        print("DataFrame Top N:")
                        print(df_top)

                        hasil_ranking_list = []
                        for _, row in df_top.iterrows():
                            skor_val = row['skor'] if 'skor' in row else 0
                            print(f"Skor untuk {row['kode_saham']}: {skor_val}")

                            if skor_val >= 0.7:
                                rekom = 'BUY'
                                rekom_color = 'success'
                                rank_color = 'warning'
                                warna = 'success'
                            elif skor_val >= 0.5:
                                rekom = 'HOLD'
                                rekom_color = 'warning'
                                rank_color = 'secondary'
                                warna = 'warning'
                            else:
                                rekom = 'SELL'
                                rekom_color = 'danger'
                                rank_color = 'secondary'
                                warna = 'danger'

                            hasil_ranking_list.append({
                                'rank': int(row['rank']) if 'rank' in row else 1,
                                'kode': row.get('kode_saham', ''),
                                'nama': row.get('nama_perusahaan', ''),
                                'skor': round(skor_val, 3),
                                'rekom': rekom,
                                'rank_color': rank_color,
                                'rekom_color': rekom_color,
                                'warna': warna,
                                'persen': int(skor_val * 100)
                            })

                        print("Hasil ranking list:", hasil_ranking_list)

                        request.session['hasil_ranking'] = hasil_ranking_list
                        request.session.modified = True

                        hasil_ranking = True
                        log_proses = [
                            {'pesan': f'Baca data saham ({len(df)} baris)', 'icon': 'check-circle', 'warna': 'success'},
                            {'pesan': 'Normalisasi data selesai (4 kriteria: ROE, EPS, PER, DER)', 'icon': 'check-circle', 'warna': 'success'},
                            {'pesan': 'Hitung skor akhir (SAW) selesai', 'icon': 'check-circle', 'warna': 'success'},
                            {'pesan': 'Ranking per sektor selesai', 'icon': 'check-circle', 'warna': 'success'},
                            {'pesan': '✅ Analisis selesai!', 'icon': 'check-circle', 'warna': 'success'},
                        ]

            except Exception as e:
                error_message = f"Terjadi kesalahan: {str(e)}"
                log_proses = [{'pesan': f'❌ Error: {str(e)}', 'icon': 'exclamation-circle', 'warna': 'danger'}]
                print("ERROR:", str(e))
        else:
            log_proses = [{'pesan': 'Tombol tidak dikenali. Pastikan Anda menekan "Jalankan Analisis".', 'icon': 'info-circle', 'warna': 'info'}]

    hasil_ranking_data = request.session.get('hasil_ranking', [])

    context = {
        'total_saham': total_saham,
        'total_sektor': total_sektor,
        'sektor_list': sektor_list,
        'bobot_tersedia': bobot_tersedia,
        'log_proses': log_proses,
        'hasil_ranking': hasil_ranking,
        'hasil_ranking_data': hasil_ranking_data,
        'error': error_message,
        'active': 'analisis'
    }
    return render(request, 'dashboard/proses_analisis.html', context)


@login_required(login_url='dashboard:login')
def hasil_ranking_admin(request):
    hasil_ranking_data = request.session.get('hasil_ranking', [])
    sektor_list = Sektor.objects.all()
    context = {
        'hasil_ranking': hasil_ranking_data,
        'sektor_list': sektor_list,
        'active': 'hasil'
    }
    return render(request, 'dashboard/hasil_ranking_admin.html', context)


@login_required(login_url='dashboard:login')
def generate_pdf(request):
    hasil_ranking = request.session.get('hasil_ranking', [])
    if not hasil_ranking:
        return HttpResponse("Tidak ada data ranking untuk dibuat PDF.", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ranking_saham_{pd.Timestamp.now().strftime("%Y%m%d_%H%M")}.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=16,
        alignment=1,
        spaceAfter=12
    )
    story.append(Paragraph("LAPORAN RANKING SAHAM", title_style))
    story.append(Spacer(1, 0.1*inch))

    sub_style = ParagraphStyle(
        'SubStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,
        textColor=colors.grey
    )
    story.append(Paragraph("Sistem Pendukung Keputusan Pemilihan Saham Menggunakan Fuzzy AHP", sub_style))
    story.append(Spacer(1, 0.2*inch))

    info_style = styles['Normal']
    story.append(Paragraph(f"<b>Sektor:</b> Perbankan  |  <b>Periode:</b> Q4-2025", info_style))
    story.append(Paragraph(f"<b>Tanggal:</b> {pd.Timestamp.now().strftime('%d-%m-%Y %H:%M')}", info_style))
    story.append(Spacer(1, 0.2*inch))

    table_data = [['Rank', 'Kode', 'Nama Perusahaan', 'Skor', 'Rekomendasi']]
    for item in hasil_ranking:
        table_data.append([
            str(item.get('rank', '')),
            item.get('kode', ''),
            item.get('nama', ''),
            str(item.get('skor', '')),
            item.get('rekom', '')
        ])

    table = Table(table_data, colWidths=[0.5*inch, 0.7*inch, 2.5*inch, 0.8*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(table)

    story.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        textColor=colors.grey
    )
    story.append(Paragraph("Shafira Salma D. | Informatika | 2026", footer_style))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


@login_required(login_url='dashboard:login')
def download_csv(request):
    hasil_ranking = request.session.get('hasil_ranking', [])
    if not hasil_ranking:
        return HttpResponse("Tidak ada data ranking untuk diunduh.", status=404)

    df = pd.DataFrame(hasil_ranking)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ranking_saham_{pd.Timestamp.now().strftime("%Y%m%d_%H%M")}.csv"'
    df.to_csv(path_or_buf=response, index=False)
    return response


@login_required(login_url='dashboard:login')
def riwayat_analisis(request):
    riwayat_list = RiwayatAnalisis.objects.all().select_related('sektor', 'user').order_by('-created_at')
    context = {
        'riwayat_list': riwayat_list,
        'total_pdf': riwayat_list.count(),
        'total_analisis': riwayat_list.count(),
        'active': 'riwayat'
    }
    return render(request, 'dashboard/riwayat_analisis.html', context)


# ========== HALAMAN API (GAMBARAN INTEGRASI) ==========
@login_required(login_url='dashboard:login')
def api_info(request):
    context = {
        'active': 'api'
    }
    return render(request, 'dashboard/api_info.html', context)


def logout_admin(request):
    logout(request)
    return redirect('dashboard:login')