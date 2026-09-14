import pandas as pd
import numpy as np

class NormalizationService:
    """Service untuk normalisasi data saham menggunakan Min-Max"""
    
    @staticmethod
    def minmax_normalization(data, sifat='BENEFIT'):
        """
        Normalisasi Min-Max untuk satu kolom data
        Benefit: (X - min) / (max - min)
        Cost: (max - X) / (max - min)
        """
        min_val = data.min()
        max_val = data.max()
        
        if min_val == max_val:
            return pd.Series([0.5] * len(data))
        
        if sifat == 'BENEFIT':
            return (data - min_val) / (max_val - min_val)
        else:  # COST
            return (max_val - data) / (max_val - min_val)
    
    @staticmethod
    def normalize_dataset(df, kriteria_list):
        """
        Normalisasi seluruh dataset berdasarkan daftar kriteria
        """
        df_normalized = df.copy()
        
        for kriteria in kriteria_list:
            if kriteria.kode in df.columns:
                sifat = kriteria.sifat
                df_normalized[kriteria.kode] = NormalizationService.minmax_normalization(
                    df[kriteria.kode], sifat
                )
        
        return df_normalized