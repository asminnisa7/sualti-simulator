"""
Uçuş kaydı: simülasyon sırasında verileri toplar ve CSV dosyasına yazar.
"""
import csv
import math
import os
import time

SUTUNLAR = [
    "zaman",
    "x", "y", "z", "bas_derece", "u", "v", "w", "r_derece_s",          # gerçek durum
    "x_tahmin", "y_tahmin", "z_tahmin", "bas_tahmin_derece",           # tahmini durum
    "z_olcum",
    "f1", "f2", "f3", "f4", "f5", "f6",                                # motor kuvvetleri (N)
    "guc_W", "batarya_yuzde", "voltaj",
    "akinti_x", "akinti_y",
    "bas_sabitleme", "hedef_bas_derece", "derinlik_sabitleme", "hedef_derinlik",
    "siradaki_kapi", "carpisma",
]


class UcusKaydi:
    def __init__(self, siklik=10.0):
        self.periyot = 1.0 / siklik
        self.sifirla()

    def sifirla(self):
        self.satirlar = []
        self.sayac = 0.0

    def adim(self, zaman, dt, durum, kestirici, iticiler, batarya, akinti_hizi, otopilot, gorev):
        self.sayac += dt
        if self.sayac + 1e-9 < self.periyot:
            return
        self.sayac -= self.periyot
        t = kestirici.durum()
        satir = [
            zaman,
            durum[0], durum[1], durum[2], math.degrees(durum[3]),
            durum[4], durum[5], durum[6], math.degrees(durum[7]),
            t[0], t[1], t[2], math.degrees(t[3]),
            kestirici.son_derinlik_olcumu,
            *iticiler.f,
            batarya.guc, batarya.doluluk * 100, batarya.voltaj,
            akinti_hizi[0], akinti_hizi[1],
            int(otopilot.bas_acik), math.degrees(otopilot.hedef_bas),
            int(otopilot.derinlik_acik), otopilot.hedef_derinlik,
            gorev.siradaki, gorev.carpisma_sayisi,
        ]
        self.satirlar.append([round(float(d), 4) for d in satir])

    def kaydet(self, klasor=None):
        """Kaydı CSV'ye yazar ve dosya yolunu döndürür (veri yoksa boş metin)."""
        if not self.satirlar:
            return ""
        if klasor is None:      # her zaman proje klasörünün içindeki kayitlar/ klasörü
            klasor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kayitlar")
        os.makedirs(klasor, exist_ok=True)
        yol = os.path.join(klasor, time.strftime("ucus_%Y%m%d_%H%M%S.csv"))
        with open(yol, "w", newline="", encoding="utf-8") as dosya:
            yazici = csv.writer(dosya)
            yazici.writerow(SUTUNLAR)
            yazici.writerows(self.satirlar)
        return yol
