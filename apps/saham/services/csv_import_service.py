import pandas as pd
from apps.sektor.models import Sektor
from apps.saham.models import Saham

class CSVImportService:
    """Service untuk membaca dan menyimpan data saham dari CSV"""
    
    REQUIRED_COLUMNS = [
        'kode_saham', 'nama_perusahaan', 'sektor', 
        'periode', 'roe', 'eps', 'per', 'der'
    ]
    
    @staticmethod
    def validate_columns(df):
        """Memeriksa apakah semua kolom wajib ada di CSV"""
        missing = [col for col in CSVImportService.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Kolom tidak ditemukan: {missing}")
        return True
    
    @staticmethod
    def clean_data(df):
        """Membersihkan dan mengkonversi tipe data"""
        numeric_cols = ['roe', 'eps', 'per', 'der']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=numeric_cols)
        return df
    
    @staticmethod
    def save_to_database(df):
        """Menyimpan data ke database, mapping sektor berdasarkan nama"""
        saved_count = 0
        for _, row in df.iterrows():
            sektor_obj, _ = Sektor.objects.get_or_create(nama=row['sektor'])
            Saham.objects.create(
                kode_saham=row['kode_saham'],
                nama_perusahaan=row['nama_perusahaan'],
                sektor=sektor_obj,
                periode=row['periode'],
                roe=row['roe'],
                eps=row['eps'],
                per=row['per'],
                der=row['der']
            )
            saved_count += 1
        return saved_count
    
    @staticmethod
    def import_csv(file_path):
        """Proses utama: baca CSV -> validasi -> bersihkan -> simpan"""
        df = pd.read_csv(file_path)
        CSVImportService.validate_columns(df)
        df_clean = CSVImportService.clean_data(df)
        total = CSVImportService.save_to_database(df_clean)
        return total
    
    @staticmethod
    def import_csv_from_dataframe(df):
        """
        Import data dari DataFrame (langsung dari upload file)
        Mencegah duplikat dengan update_or_create berdasarkan kode_saham dan periode
        """
        # Validasi kolom
        CSVImportService.validate_columns(df)
        
        # Bersihkan data
        df_clean = CSVImportService.clean_data(df)
        
        saved_count = 0
        for _, row in df_clean.iterrows():
            # Cari atau buat sektor
            sektor_obj, _ = Sektor.objects.get_or_create(nama=row['sektor'])
            
            # Update atau create (mencegah duplikat)
            Saham.objects.update_or_create(
                kode_saham=row['kode_saham'],
                periode=row['periode'],
                defaults={
                    'nama_perusahaan': row['nama_perusahaan'],
                    'sektor': sektor_obj,
                    'roe': row['roe'],
                    'eps': row['eps'],
                    'per': row['per'],
                    'der': row['der']
                }
            )
            saved_count += 1
        
        return saved_count