from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import pandas as pd

from apps.saham.models import Saham
from apps.sektor.models import Sektor
from apps.kriteria.models import Kriteria
from apps.analisis.services.normalization import NormalizationService
from apps.analisis.services.ranking import RankingService


def beranda(request):
    return render(request, 'landing/beranda.html', {'active': 'beranda'})


def data_saham(request):
    saham_list = Saham.objects.all().select_related('sektor')
    return render(request, 'landing/data_saham.html', {
        'saham_list': saham_list,
        'active': 'data_saham'
    })


def proses_analisis(request):
    saham_list = Saham.objects.all().select_related('sektor')
    sektor_list = Sektor.objects.all()

    if request.method == 'POST':
        saham_ids = request.POST.getlist('saham_ids')
        if not saham_ids or len(saham_ids) < 2:
            messages.error(request, 'Pilih minimal 2 saham untuk dibandingkan.')
            return render(request, 'landing/proses_analisis.html', {
                'saham_list': saham_list,
                'sektor_list': sektor_list,
                'active': 'proses'
            })

        saham_terpilih = Saham.objects.filter(id__in=saham_ids).select_related('sektor')
        if saham_terpilih.count() < 2:
            messages.error(request, 'Pilih minimal 2 saham yang valid.')
            return render(request, 'landing/proses_analisis.html', {
                'saham_list': saham_list,
                'sektor_list': sektor_list,
                'active': 'proses'
            })

        bobot_dict = {k.kode: k.bobot for k in Kriteria.objects.all() if k.bobot > 0}
        if not bobot_dict:
            messages.error(request, 'Bobot kriteria belum dihitung oleh admin. Silakan coba lagi nanti.')
            return render(request, 'landing/proses_analisis.html', {
                'saham_list': saham_list,
                'sektor_list': sektor_list,
                'active': 'proses'
            })

        # ================================================================
        # AMBIL DATA
        # ================================================================
        data = []
        for s in saham_terpilih:
            data.append({
                'kode_saham': s.kode_saham,
                'nama_perusahaan': s.nama_perusahaan,
                'sektor': s.sektor.nama if s.sektor else '',
                'periode': s.periode,
                'roe': float(s.roe) if s.roe else 0.0,
                'eps': float(s.eps) if s.eps else 0.0,
                'per': float(s.per) if s.per else 0.0,
                'der': float(s.der) if s.der else 0.0,
                'bi_rate': float(s.bi_rate) if s.bi_rate else 0.0,
            })
        df = pd.DataFrame(data)

        # ================================================================
        # AMBIL MODE RANKING
        # ================================================================
        mode_ranking = request.POST.get('mode_ranking', 'per_sektor')
        print(f"DEBUG: Mode ranking = {mode_ranking}")

        kriteria_sifat = {k.kode: k.sifat for k in Kriteria.objects.all()}

        # ================================================================
        # NORMALISASI PER SEKTOR (untuk mode per_sektor)
        # ================================================================
        if mode_ranking == 'per_sektor':
            # Normalisasi per sektor
            df_normalized = df.copy()
            for sektor in df['sektor'].unique():
                mask = df['sektor'] == sektor
                for col in ['roe', 'eps', 'per', 'der']:
                    if col in df.columns:
                        sifat = kriteria_sifat.get(col.upper(), 'BENEFIT')
                        # Normalisasi hanya untuk data di sektor ini
                        df_normalized.loc[mask, col] = NormalizationService.minmax_normalization(
                            df.loc[mask, col], sifat
                        )
            # Hitung skor
            skor = RankingService.hitung_skor_akhir(df_normalized, bobot_dict)
            # Ranking per sektor
            df_result = RankingService.ranking_per_sektor(df_normalized, skor, 'sektor')

        else:
            # Normalisasi global (untuk all_sektor)
            df_normalized = df.copy()
            for col in ['roe', 'eps', 'per', 'der']:
                if col in df.columns:
                    sifat = kriteria_sifat.get(col.upper(), 'BENEFIT')
                    df_normalized[col] = NormalizationService.minmax_normalization(df[col], sifat)

            skor = RankingService.hitung_skor_akhir(df_normalized, bobot_dict)
            df_result = RankingService.ranking_global(df_normalized, skor)

        print(f"DEBUG: Jumlah data hasil = {len(df_result)}")

        # ================================================================
        # LOOP UNTUK MEMBUAT HASIL
        # ================================================================
        bobot_roe = bobot_dict.get('ROE', 0)
        bobot_eps = bobot_dict.get('EPS', 0)
        bobot_per = bobot_dict.get('PER', 0)
        bobot_der = bobot_dict.get('DER', 0)

        hasil = []
        for idx, row in df_result.iterrows():
            skor_val = row['skor']

            if skor_val >= 0.7:
                rekom = 'BUY'
                rekom_color = 'success'
                rank_color = 'warning'
            elif skor_val >= 0.5:
                rekom = 'HOLD'
                rekom_color = 'warning'
                rank_color = 'secondary'
            else:
                rekom = 'SELL'
                rekom_color = 'danger'
                rank_color = 'secondary'

            # Ambil nilai normalisasi dari df_normalized (baris sesuai indeks)
            norm_row = df_normalized.iloc[idx]
            kontribusi_roe = round(norm_row['roe'] * bobot_roe, 3)
            kontribusi_eps = round(norm_row['eps'] * bobot_eps, 3)
            kontribusi_per = round(norm_row['per'] * bobot_per, 3)
            kontribusi_der = round(norm_row['der'] * bobot_der, 3)

            # Buat kesimpulan
            if skor_val >= 0.7:
                if kontribusi_roe >= kontribusi_eps and kontribusi_roe >= kontribusi_per and kontribusi_roe >= kontribusi_der:
                    kesimpulan = "ROE yang sangat tinggi menjadi pendorong utama. Perusahaan sangat efisien dalam menghasilkan laba dari modal sendiri."
                elif kontribusi_per >= kontribusi_eps and kontribusi_per >= kontribusi_der:
                    kesimpulan = "PER yang baik menunjukkan saham ini masih undervalued atau memiliki valuasi yang wajar."
                else:
                    kesimpulan = "Fundamental saham ini sangat kuat secara keseluruhan. Layak dipertimbangkan untuk dibeli."
            elif skor_val >= 0.5:
                if kontribusi_der > 0.03:
                    kesimpulan = "DER cukup tinggi, perlu diperhatikan risiko keuangan. Namun secara umum masih layak dipertahankan."
                elif kontribusi_per < 0.05:
                    kesimpulan = "PER kurang baik, valuasi mungkin terlalu mahal. Disarankan untuk tahan sambil memantau."
                else:
                    kesimpulan = "Saham ini cukup baik, namun ada beberapa indikator yang perlu diperhatikan lebih lanjut."
            else:
                if kontribusi_roe < 0.1:
                    kesimpulan = "ROE rendah, perusahaan kurang efisien dalam menghasilkan laba. Kurang kompetitif."
                elif kontribusi_der > 0.05:
                    kesimpulan = "DER tinggi, risiko keuangan cukup besar. Tidak direkomendasikan."
                else:
                    kesimpulan = "Fundamental kurang kompetitif dibandingkan emiten lain di sektor yang sama."

            hasil.append({
                'rank': int(row['rank']),
                'kode': row['kode_saham'],
                'nama': row['nama_perusahaan'],
                'sektor': row['sektor'],
                'skor': round(skor_val, 3),
                'rank_color': rank_color,
                'rekom': rekom,
                'rekom_color': rekom_color,
                'warna': 'success' if rekom == 'BUY' else 'warning' if rekom == 'HOLD' else 'danger',
                'persen': int(skor_val * 100),
                'kontribusi_roe': kontribusi_roe,
                'kontribusi_eps': kontribusi_eps,
                'kontribusi_per': kontribusi_per,
                'kontribusi_der': kontribusi_der,
                'bi_rate': row.get('bi_rate', 0.0),
                'kesimpulan': kesimpulan,
            })

        # ================================================================
        # SIMPAN KE SESSION
        # ================================================================
        request.session['hasil_user'] = hasil
        request.session['mode_ranking'] = mode_ranking
        return redirect('hasil_rekomendasi')

    return render(request, 'landing/proses_analisis.html', {
        'saham_list': saham_list,
        'sektor_list': sektor_list,
        'active': 'proses'
    })


def hasil_rekomendasi(request):
    hasil = request.session.get('hasil_user', [])
    mode = request.session.get('mode_ranking', 'per_sektor')
    if not hasil:
        messages.info(request, 'Silakan pilih saham terlebih dahulu di halaman Proses Analisis.')
        return redirect('proses_analisis')
    return render(request, 'landing/hasil_rekomendasi.html', {
        'hasil': hasil,
        'mode': mode,
        'active': 'hasil'
    })


def tentang_metode(request):
    return render(request, 'landing/tentang_metode.html', {'active': 'tentang'})


def generate_pdf_user(request):
    hasil = request.session.get('hasil_user', [])
    if not hasil:
        return HttpResponse("Tidak ada data ranking untuk dibuat PDF.", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ranking_saham_user_{pd.Timestamp.now().strftime("%Y%m%d_%H%M")}.pdf"'

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
    story.append(Paragraph(f"<b>Tanggal:</b> {pd.Timestamp.now().strftime('%d-%m-%Y %H:%M')}", info_style))
    story.append(Spacer(1, 0.2*inch))

    table_data = [['Rank', 'Kode', 'Nama Perusahaan', 'Skor', 'Rekomendasi', 'Kesimpulan']]
    for item in hasil:
        table_data.append([
            str(item.get('rank', '')),
            item.get('kode', ''),
            item.get('nama', ''),
            str(item.get('skor', '')),
            item.get('rekom', ''),
            item.get('kesimpulan', '')
        ])

    table = Table(table_data, colWidths=[0.5*inch, 0.7*inch, 2.0*inch, 0.8*inch, 1.0*inch, 2.0*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
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