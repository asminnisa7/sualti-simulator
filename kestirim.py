"""
Durum kestirimi: gürültülü sensör ölçümlerinden aracın durumunu tahmin etme.

  Derinlik : Kalman filtresi (durum: derinlik ve dikey hız; motor kuvvetini de bilir)
  Baş açısı: tamamlayıcı filtre (jiroskop + pusula), jiroskop kaymasını da öğrenir
  Konum    : ölü hesap (DVL hızı + tahmini baş açısı ile konumu biriktirme);
             kamera bir kapıyı görünce, kapının haritadaki bilinen yeriyle düzeltilir
"""
import math

import numpy as np

import ayarlar as A
from fizik import M, surtunme
from kontrol import aci_farki


class DerinlikKalman:
    """Durum: [z, w]. Model: hareket denklemi (motor kuvvetiyle) + rastgele ivme. Ölçüm: z."""

    def __init__(self, z0):
        self.x = np.array([z0, 0.0])                 # tahmin
        self.P = np.diag([0.1, 0.1])                 # tahminin belirsizliği
        self.R = A.DERINLIK_SENSORU[1] ** 2          # ölçüm gürültüsü (varyans)

    def tahmin_et(self, dt, motor_kuvveti):
        """Model ile bir adım ileriyi tahmin et. Motorların dikey kuvveti bilindiği için
        beklenen ivme hesaplanabilir: a = (motor + ağırlık - kaldırma - sürtünme) / kütle"""
        z, w = self.x
        ivme = (motor_kuvveti + A.AGIRLIK - A.KALDIRMA - surtunme(w, A.K_DIKEY)) / M[2]
        self.x = np.array([z + w * dt + 0.5 * ivme * dt ** 2, w + ivme * dt])
        F = np.array([[1.0, dt], [0.0, 1.0]])
        q = A.KALMAN_IVME_GURULTUSU ** 2
        Q = q * np.array([[dt ** 4 / 4, dt ** 3 / 2], [dt ** 3 / 2, dt ** 2]])
        self.P = F @ self.P @ F.T + Q

    def duzelt(self, olcum):
        H = np.array([1.0, 0.0])
        S = H @ self.P @ H + self.R                  # beklenen hata varyansı
        K = self.P @ H / S                           # Kalman kazancı: ölçüme ne kadar güvenilecek
        self.x = self.x + K * (olcum - H @ self.x)
        self.P = (np.eye(2) - np.outer(K, H)) @ self.P


class Kestirici:
    def __init__(self, durum):
        self.sifirla(durum)

    def sifirla(self, durum):
        self.kalman = DerinlikKalman(durum[2])
        self.x, self.y = durum[0], durum[1]          # başlangıç konumu bilinir
        self.psi = durum[3]
        self.r = 0.0
        self.kayma = 0.0                             # tahmini jiroskop kayması
        self.u = self.v = 0.0
        self.son_derinlik_olcumu = durum[2]
        self.kapi_goruldu = None                     # son görülen kapı (arayüz için)
        self._gorus_suresi = 0.0

    def guncelle(self, olcumler, motor_kuvveti, dt):
        """motor_kuvveti: motorların toplam [ileri, yan, dikey, tork] kuvveti (yazılım bunu bilir)."""
        # --- Derinlik: Kalman ---
        self.kalman.tahmin_et(dt, motor_kuvveti[2])
        if olcumler["derinlik"] is not None:
            self.kalman.duzelt(olcumler["derinlik"])
            self.son_derinlik_olcumu = olcumler["derinlik"]

        # --- Baş açısı: tamamlayıcı filtre ---
        if olcumler["jiroskop"] is not None:
            self.r = olcumler["jiroskop"] - self.kayma   # öğrenilen kaymayı çıkar
        self.psi += self.r * dt                      # jiroskopu entegre et (hızlı ama kayar)
        if olcumler["pusula"] is not None:           # pusulayla yavaşça düzelt (kaymaz)
            hata = aci_farki(olcumler["pusula"] - self.psi)
            self.psi += A.PUSULA_DUZELTME * hata
            self.kayma -= A.KAYMA_OGRENME * hata     # sürekli aynı yöne hata = jiroskop kayıyor
        self.psi = aci_farki(self.psi)

        # --- Konum: ölü hesap ---
        if olcumler["dvl_u"] is not None:
            self.u = olcumler["dvl_u"]
        if olcumler["dvl_v"] is not None:
            self.v = olcumler["dvl_v"]
        c, s = math.cos(self.psi), math.sin(self.psi)
        self.x += (c * self.u - s * self.v) * dt
        self.y += (s * self.u + c * self.v) * dt

    def kapi_ile_duzelt(self, olcum, kapilar, dt):
        """Kamera ölçümüyle konum düzeltmesi (bilinen yer işaretine göre konumlama).
        Kapının araca göre ölçülen konumu, tahmini konum ve yönle haritaya taşınır;
        haritadaki gerçek yeriyle arasındaki fark kadar tahmin kaydırılır."""
        self._gorus_suresi = max(0.0, self._gorus_suresi - dt)
        if self._gorus_suresi == 0.0:
            self.kapi_goruldu = None
        if olcum is None:
            return
        no, ileri, yan = olcum
        kapi = kapilar[no]
        c, s = math.cos(self.psi), math.sin(self.psi)
        tahmini_kapi_x = self.x + c * ileri - s * yan
        tahmini_kapi_y = self.y + s * ileri + c * yan
        self.x += A.KAPI_DUZELTME * (kapi.x - tahmini_kapi_x)
        self.y += A.KAPI_DUZELTME * (kapi.y - tahmini_kapi_y)
        self.kapi_goruldu = no
        self._gorus_suresi = 0.3

    def durum(self):
        """Otopilotun kullanacağı tahmini durum: [x, y, z, psi, u, v, w, r]"""
        z, w = self.kalman.x
        return np.array([self.x, self.y, z, self.psi, self.u, self.v, w, self.r])
