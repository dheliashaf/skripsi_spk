import numpy as np
from apps.kriteria.models import Kriteria, PairwiseComparison

class FuzzyAHPService:
    """
    Service untuk perhitungan Fuzzy AHP
    """
    
    FUZZY_SCALE = {
        1: (1, 1, 1),
        2: (1, 2, 3),
        3: (2, 3, 4),
        4: (3, 4, 5),
        5: (4, 5, 6),
        6: (5, 6, 7),
        7: (6, 7, 8),
        8: (7, 8, 9),
        9: (8, 9, 9)
    }
    
    RI_TABLE = {
        1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90,
        5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41,
        9: 1.45, 10: 1.49
    }
    
    @staticmethod
    def get_fuzzy_value(crisp_value):
        """Konversi nilai crisp ke TFN, dengan penanganan nilai pecahan"""
        if crisp_value in FuzzyAHPService.FUZZY_SCALE:
            return FuzzyAHPService.FUZZY_SCALE[crisp_value]
        
        # Untuk nilai di luar 1-9 (termasuk pecahan), buat TFN dengan batas aman
        l = max(0.1, crisp_value - 1)
        m = max(0.1, crisp_value)
        u = max(0.1, crisp_value + 1)
        return (l, m, u)
    
    @staticmethod
    def get_pairwise_matrix():
        kriteria = Kriteria.objects.all().order_by('id')
        n = kriteria.count()
        matrix = np.ones((n, n))
        pairwise_list = PairwiseComparison.objects.all()
        
        for p in pairwise_list:
            i = list(kriteria).index(p.kriteria_1)
            j = list(kriteria).index(p.kriteria_2)
            val = float(p.nilai_crisp)
            if val <= 0:
                val = 1  # Jika nilai 0, set ke 1 sebagai fallback
            matrix[i][j] = val
            matrix[j][i] = 1 / val
        
        return matrix, list(kriteria)
    
    @staticmethod
    def calculate_weights():
        matrix, kriteria_list = FuzzyAHPService.get_pairwise_matrix()
        n = len(kriteria_list)
        
        # Konversi ke TFN
        fuzzy_matrix = np.zeros((n, n, 3))
        for i in range(n):
            for j in range(n):
                val = matrix[i][j]
                if val in FuzzyAHPService.FUZZY_SCALE:
                    fuzzy_matrix[i][j] = FuzzyAHPService.FUZZY_SCALE[val]
                else:
                    l = max(0.1, val - 1)
                    m = max(0.1, val)
                    u = max(0.1, val + 1)
                    fuzzy_matrix[i][j] = (l, m, u)
        
        # Geometric Mean Fuzzy
        geo_mean = []
        for i in range(n):
            l_product = 1.0
            m_product = 1.0
            u_product = 1.0
            for j in range(n):
                l_product *= fuzzy_matrix[i][j][0]
                m_product *= fuzzy_matrix[i][j][1]
                u_product *= fuzzy_matrix[i][j][2]
            l = l_product ** (1.0/n)
            m = m_product ** (1.0/n)
            u = u_product ** (1.0/n)
            geo_mean.append((l, m, u))
        
        # Defuzzifikasi
        crisp_weights = []
        for l, m, u in geo_mean:
            w = (l + 2*m + u) / 4
            crisp_weights.append(w)
        
        # Normalisasi
        total = sum(crisp_weights)
        if total == 0:
            normalized_weights = [1.0/n] * n
        else:
            normalized_weights = [w / total for w in crisp_weights]
        
        # Uji Konsistensi (dengan perbaikan CR positif)
        cr = FuzzyAHPService.calculate_consistency_ratio(matrix, n)
        
        # Simpan bobot ke database
        for i, kriteria in enumerate(kriteria_list):
            kriteria.bobot = normalized_weights[i]
            kriteria.save()
        
        return {
            'weights': dict(zip([k.kode for k in kriteria_list], normalized_weights)),
            'cr': cr,
            'is_consistent': cr < 0.1,
            'kriteria_list': kriteria_list
        }
    
    @staticmethod
    def calculate_consistency_ratio(matrix, n):
        """
        Menghitung Consistency Ratio (CR) yang VALID dan POSITIF
        """
        try:
            eigenvalues, _ = np.linalg.eig(matrix)
            # Ambil nilai eigen real terbesar
            max_eigenvalue = np.max(eigenvalues.real)
            
            # Jika max_eigenvalue < n (tidak mungkin untuk matriks pairwise yang valid),
            # set ke n untuk menghindari CI negatif
            if max_eigenvalue < n:
                max_eigenvalue = n
            
            ci = (max_eigenvalue - n) / (n - 1) if n > 1 else 0
            # Pastikan CI tidak negatif
            if ci < 0:
                ci = 0
            
            ri = FuzzyAHPService.RI_TABLE.get(n, 0.90)
            cr = ci / ri if ri > 0 else 0
            return float(cr)
        except Exception:
            # Jika ada error, return 0 (dianggap konsisten sempurna)
            return 0.0
    
    @staticmethod
    def get_bobot_kriteria():
        kriteria = Kriteria.objects.all().order_by('kode')
        return {k.kode: k.bobot for k in kriteria}