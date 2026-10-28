"""
Su efektleri:
  Kabarciklar : motorların püskürttüğü su ve kabarcıklar (motor gücüyle orantılı)
  Kostik      : su yüzeyinden kırılan ışığın havuz tabanında oluşturduğu hareketli desen
"""
import math
import random

import numpy as np
import pygame

import ayarlar as A


class Kabarciklar:
    def __init__(self):
        self.liste = []          # [x, y, z, vx, vy, vz, ömür, başlangıç ömrü]
        self._birikim = [0.0] * len(A.ITICILER)

    def sifirla(self):
        self.liste.clear()

    def guncelle(self, durum, motor_kuvvetleri, akinti, dt):
        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        c, s = math.cos(psi), math.sin(psi)
        for i, ((ad, mx, my, aci, dikey), f) in enumerate(zip(A.ITICILER, motor_kuvvetleri)):
            oran = abs(f) / A.ITICI_ILERI_MAX
            if oran < 0.08:
                continue
            self._birikim[i] += oran * 45 * dt                       # saniyede en çok ~45 kabarcık
            while self._birikim[i] >= 1.0 and len(self.liste) < 450:
                self._birikim[i] -= 1.0
                isaret = 1 if f > 0 else -1
                if dikey:
                    bz = -0.04
                    jet = (0.0, 0.0, -isaret)                          # su itkinin tersine püskürür
                else:
                    bz = 0.05
                    a = math.radians(aci)
                    jx, jy = -isaret * math.cos(a), -isaret * math.sin(a)
                    jet = (jx * c - jy * s, jx * s + jy * c, 0.0)
                px = x + mx * c - my * s + random.uniform(-0.02, 0.02)
                py = y + mx * s + my * c + random.uniform(-0.02, 0.02)
                hiz = 0.6 + 0.9 * oran
                omur = random.uniform(1.6, 2.8)
                self.liste.append([px, py, z + bz, jet[0] * hiz + random.uniform(-0.1, 0.1),
                                   jet[1] * hiz + random.uniform(-0.1, 0.1),
                                   jet[2] * hiz + random.uniform(-0.05, 0.05), omur, omur])
        kalan = []
        sonum = math.exp(-2.5 * dt)
        for k in self.liste:
            k[3] *= sonum
            k[4] *= sonum
            k[5] += (-0.3 - k[5]) * min(1.0, 2.0 * dt)               # kabarcık yavaşça yükselir
            k[0] += (k[3] + akinti[0]) * dt
            k[1] += (k[4] + akinti[1]) * dt
            k[2] += k[5] * dt
            k[6] -= dt
            if k[6] > 0 and k[2] > 0.02:
                kalan.append(k)
        self.liste = kalan


class Kostik:
    """Havuz tabanındaki ışık deseni: kendini tekrar eden bir doku, iki katman halinde kayar."""
    KARO_M = 2.5                     # bir dokunun dünyadaki boyu (m)

    def __init__(self):
        N = 160
        i = np.arange(N)
        X, Y = np.meshgrid(i, i, indexing="ij")
        a = 2 * np.pi / N
        w = np.sin(4 * a * X + 1.8 * np.sin(3 * a * Y)) * np.sin(4 * a * Y + 1.8 * np.sin(3 * a * X + 1.0))
        c = (1 - np.abs(w)) ** 10                                  # ince parlak çizgiler ağı
        renk = np.stack([c * 12, c * 24, c * 28], axis=-1).astype(np.uint8)
        self.doku = pygame.surfarray.make_surface(renk)
        self._olcekli = {}

    def _doku(self, piksel):
        if piksel not in self._olcekli:
            if len(self._olcekli) > 6:
                self._olcekli.clear()
            self._olcekli[piksel] = pygame.transform.smoothscale(self.doku, (piksel, piksel))
        return self._olcekli[piksel]

    def ciz(self, ekran, piksel_fonk, olcek, gorunen, zaman):
        """gorunen: (x0, y0, x1, y1) dünya koordinatlarında görünen havuz bölgesi."""
        boy = max(8, int(self.KARO_M * olcek))
        doku = self._doku(boy)
        for kx, ky in ((0.11 * zaman, 0.07 * zaman), (-0.08 * zaman + 1.1, 0.1 * zaman + 0.7)):
            x0 = math.floor((gorunen[0] - kx) / self.KARO_M) * self.KARO_M + kx
            y0 = math.floor((gorunen[1] - ky) / self.KARO_M) * self.KARO_M + ky
            x = x0
            while x < gorunen[2]:
                y = y0
                while y < gorunen[3]:
                    ekran.blit(doku, piksel_fonk(x, y), special_flags=pygame.BLEND_ADD)
                    y += self.KARO_M
                x += self.KARO_M
