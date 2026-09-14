import os
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from datetime import datetime

class PDFGeneratorService:
    """Service untuk generate PDF laporan ranking"""
    
    @staticmethod
    def generate_pdf(data_ranking, judul="Laporan Ranking Saham"):
        """
        Generate PDF dari data ranking
        """
        # Template HTML untuk PDF
        html_content = render_to_string('laporan/pdf_template.html', {
            'judul': judul,
            'data': data_ranking,
            'tanggal': datetime.now().strftime('%d-%m-%Y %H:%M'),
        })
        
        # Generate PDF
        pdf_file = HTML(string=html_content).write_pdf()
        
        return pdf_file
    
    @staticmethod
    def save_pdf(pdf_content, filename):
        """
        Simpan PDF ke media/pdf_results/
        """
        path = os.path.join(settings.MEDIA_ROOT, 'pdf_results', filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'wb') as f:
            f.write(pdf_content)
        
        return f'pdf_results/{filename}'