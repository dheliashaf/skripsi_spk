import pandas as pd

class RankingService:
    """Service untuk perhitungan skor dan ranking saham"""
    
    @staticmethod
    def hitung_skor_akhir(df_normalized, bobot_dict):
        """
        Menghitung skor akhir menggunakan metode SAW
        Skor = Σ (bobot_kriteria × nilai_normalisasi)
        """
        skor = pd.Series([0] * len(df_normalized))
        for kriteria, bobot in bobot_dict.items():
            col = kriteria.lower()
            if col in df_normalized.columns:
                skor += df_normalized[col] * bobot
        return skor
    
    @staticmethod
    def ranking_per_sektor(df, skor, sektor_col='sektor'):
        """Ranking per sektor (apple-to-apple)"""
        df_result = df.copy()
        df_result['skor'] = skor
        df_result['rank'] = df_result.groupby(sektor_col)['skor'].rank(
            ascending=False, method='min'
        )
        return df_result.sort_values([sektor_col, 'skor'], ascending=[True, False])
    
    @staticmethod
    def ranking_global(df, skor):
        """Ranking global (semua sektor) — TAMBAHKAN INI!"""
        df_result = df.copy()
        df_result['skor'] = skor
        df_result['rank'] = df_result['skor'].rank(ascending=False, method='min')
        return df_result.sort_values('skor', ascending=False)
    
    @staticmethod
    def top_n_saham(df_ranked, n=5):
        return df_ranked[df_ranked['rank'] <= n]