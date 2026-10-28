"""
Batarya ve güç tüketimi modeli.

Motor gücü (momentum / pervane disk teorisi):
    P_ideal = |F|^1.5 / sqrt(2 * rho * A)
    P_elektrik = P_ideal / verim
Yani itkiyi 2 katına çıkarmak gücü yaklaşık 2.8 katına çıkarır.
"""
import math

import ayarlar as A

_PAYDA = math.sqrt(2.0 * A.SU_YOGUNLUGU * A.PERVANE_ALANI) * A.ITICI_VERIM


def motor_gucu(f):
    """Bir motorun f Newton itki için harcadığı elektrik gücü (W)."""
    return abs(f) ** 1.5 / _PAYDA


class Batarya:
    def __init__(self):
        self.kapasite_wh = A.BATARYA_AH * A.V_NOMINAL
        self.sifirla()

    def sifirla(self):
        self.kalan_wh = self.kapasite_wh
        self.guc = 0.0
        self.akim = 0.0
        self.voltaj = A.V_DOLU

    @property
    def doluluk(self):
        return self.kalan_wh / self.kapasite_wh

    def adim(self, motor_kuvvetleri, dt):
        if self.kalan_wh <= 0:
            self.guc = self.akim = 0.0
            self.voltaj = A.V_BOS
            return
        self.guc = A.ELEKTRONIK_GUC + sum(motor_gucu(f) for f in motor_kuvvetleri)
        acik_devre = A.V_BOS + (A.V_DOLU - A.V_BOS) * self.doluluk
        self.akim = self.guc / acik_devre
        self.voltaj = acik_devre - self.akim * A.IC_DIRENC      # yük altında voltaj düşer
        self.akim = self.guc / self.voltaj
        self.kalan_wh = max(0.0, self.kalan_wh - self.guc * dt / 3600.0)

    def itki_carpani(self):
        """Motorların üretebileceği en büyük itki voltajla orantılı düşer."""
        if self.kalan_wh <= 0:
            return 0.0
        return min(1.0, self.voltaj / A.V_ITKI_REF)

    def kalan_dakika(self):
        """Şu anki tüketim sürerse batarya kaç dakika daha gider?"""
        if self.guc <= 0:
            return float("inf")
        return self.kalan_wh / self.guc * 60.0
