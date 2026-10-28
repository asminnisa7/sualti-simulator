"""
Motor (itici) modeli:
  1) Yerleşim matrisi T:  araca etki eden kuvvetler = T @ motor_kuvvetleri
  2) İtki dağıtımı: istenen kuvvetlerden her motorun kuvvetini bulma
  3) Motor sınırları (doyum)
  4) Motor gecikmesi
"""
import math
import numpy as np

import ayarlar as A


class Iticiler:
    def __init__(self):
        self.liste = A.ITICILER
        sutunlar = []
        for ad, mx, my, aci, dikey in self.liste:
            if dikey:
                # Dikey motor sadece aşağı-yukarı kuvvet üretir (+ = aşağı)
                sutunlar.append([0.0, 0.0, 1.0, 0.0])
            else:
                a = math.radians(aci)
                fx, fy = math.cos(a), math.sin(a)
                tork = mx * fy - my * fx          # moment = konum x kuvvet
                sutunlar.append([fx, fy, 0.0, tork])

        # T: 4 satır (ileri, yan, dikey, tork) x 6 sütun (motorlar)
        self.T = np.array(sutunlar).T
        # Sözde ters: istenen hareketi motorları en az zorlayarak üreten çözüm
        self.T_ters = np.linalg.pinv(self.T)
        self.dikey_mi = np.array([m[4] for m in self.liste])

        self.guc_carpani = 1.0                   # batarya voltajına bağlı itki sınırı çarpanı
        self.komut = np.zeros(len(self.liste))   # motorlara gönderilen komut (N)
        self.f = np.zeros(len(self.liste))       # motorların o anki gerçek kuvveti (N)

    def sinir(self, f):
        temel = A.ITICI_ILERI_MAX if f >= 0 else A.ITICI_GERI_MAX
        return temel * self.guc_carpani

    def dagit(self, istenen):
        """İstenen [ileri, yan, dikey, tork] -> her motorun komutu."""
        if self.guc_carpani <= 0:                # batarya bitti: motorlar durur
            self.komut = np.zeros(len(self.liste))
            return
        f = self.T_ters @ np.array(istenen, dtype=float)
        # Sınırı aşan motor varsa o gruptaki (yatay ya da dikey) tüm motorları
        # aynı oranda kıs: böylece hareketin yönü bozulmaz.
        for grup in (~self.dikey_mi, self.dikey_mi):
            oranlar = [abs(fi) / self.sinir(fi) for fi in f[grup]]
            en_buyuk = max(oranlar)
            if en_buyuk > 1.0:
                f[grup] = f[grup] / en_buyuk
        self.komut = f

    def adim(self, dt):
        """Motor gecikmesi: gerçek kuvvet komuta yavaşça yaklaşır."""
        alfa = 1.0 - math.exp(-dt / A.ITICI_ZAMAN_SABITI)
        self.f = self.f + alfa * (self.komut - self.f)

    def toplam_kuvvet(self):
        """Motorların araca uyguladığı toplam [ileri, yan, dikey, tork]."""
        return self.T @ self.f
