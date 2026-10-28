"""
BlueROV2 Heavy benzeri 3B araç modeli.

Model basit parçalardan (kutu, silindir) kurulur ve üç görünümde de kullanılır:
  - 3B takip kamerası (perspektif)
  - üstten görünüm (yukarıdan dik izdüşüm)
  - yan kesit (yandan dik izdüşüm)

Her yüz ışık yönüne göre gölgelendirilir (düz gölgelendirme) ve yüzler
uzaktan yakına sıralanarak çizilir (ressam algoritması).
Gövde ekseni: x ileri, y sağa, z aşağı (metre).
"""
import math

import numpy as np
import pygame

import ayarlar as A

# Renkler
SARI = (246, 190, 40)        # yüzdürme köpüğü
SIYAH = (34, 36, 42)         # çerçeve plakaları
KOYU = (52, 56, 64)
TUP = (150, 186, 204)        # şeffaf akrilik elektronik tüpü
KUBBE = (110, 168, 205)
BATARYA = (66, 70, 78)
MOTOR = (40, 43, 50)
HALKA = (92, 98, 108)
PERVANE = (175, 180, 188)
ISIK = (255, 246, 214)
KAMERA = (12, 14, 18)

ISIK_YONU = np.array([0.35, -0.25, 1.0]) / np.linalg.norm([0.35, -0.25, 1.0])   # yukarıdan aşağı


class AracModeli:
    def __init__(self):
        self.koseler = []            # gövde eksenindeki köşe noktaları
        self.yuzler = []             # (köşe indeksleri, gövde normali, renk, çift yüzlü mü)
        self._kur()
        self.statik_koseler = np.array(self.koseler, dtype=float)
        self.statik_yuzler = list(self.yuzler)
        # yüz özellikleri dizi halinde (her karede toplu hesap için)
        self._s_merkez = np.array([self.statik_koseler[idx].mean(axis=0) for idx, *_ in self.statik_yuzler])
        self._s_normal = np.array([n for _, n, _, _ in self.statik_yuzler])
        self._s_renk = np.array([r for _, _, r, _ in self.statik_yuzler], dtype=float)
        self._s_cift = np.array([c for *_, c in self.statik_yuzler])
        self._s_kenar = np.array([r != PERVANE for _, _, r, _ in self.statik_yuzler])
        self.pervane_acisi = [0.0] * len(A.ITICILER)
        # her motorun pervane merkezi ve dönme düzlemi (bir kez hesaplanır)
        self._pervane_eksen = []
        for ad, mx, my, aci, dikey in A.ITICILER:
            if dikey:
                m, e = np.array([mx, my, -0.04]), np.array([0, 0, 1.0])
            else:
                a = math.radians(aci)
                m, e = np.array([mx, my, 0.05]), np.array([math.cos(a), math.sin(a), 0.0])
            yard = np.array([0, 0, 1.0]) if abs(e[2]) < 0.9 else np.array([1.0, 0, 0])
            u = np.cross(e, yard)
            u /= np.linalg.norm(u)
            self._pervane_eksen.append((m, e, u, np.cross(e, u)))
        self._kanat_aci = np.array([-0.22, -0.35, 0.35, 0.22])
        self._kanat_r = np.array([0.012, 0.037, 0.037, 0.012])
        self.on_isiklar = [(0.215, -0.09, -0.03), (0.215, 0.09, -0.03)]

    # ------------------------------------------------------------ #
    # Parçalar
    # ------------------------------------------------------------ #
    def _kose(self, p):
        self.koseler.append(tuple(p))
        return len(self.koseler) - 1

    def _yuz(self, indeksler, normal, renk, cift=False):
        self.yuzler.append((indeksler, np.array(normal, dtype=float), renk, cift))

    def kutu(self, merkez, boyut, renk):
        cx, cy, cz = merkez
        hx, hy, hz = boyut[0] / 2, boyut[1] / 2, boyut[2] / 2
        k = {}
        for a in (-1, 1):
            for b in (-1, 1):
                for c in (-1, 1):
                    k[(a, b, c)] = self._kose((cx + a * hx, cy + b * hy, cz + c * hz))
        self._yuz([k[(1, -1, -1)], k[(1, 1, -1)], k[(1, 1, 1)], k[(1, -1, 1)]], (1, 0, 0), renk)
        self._yuz([k[(-1, -1, -1)], k[(-1, -1, 1)], k[(-1, 1, 1)], k[(-1, 1, -1)]], (-1, 0, 0), renk)
        self._yuz([k[(-1, 1, -1)], k[(-1, 1, 1)], k[(1, 1, 1)], k[(1, 1, -1)]], (0, 1, 0), renk)
        self._yuz([k[(-1, -1, -1)], k[(1, -1, -1)], k[(1, -1, 1)], k[(-1, -1, 1)]], (0, -1, 0), renk)
        self._yuz([k[(-1, -1, -1)], k[(-1, 1, -1)], k[(1, 1, -1)], k[(1, -1, -1)]], (0, 0, -1), renk)
        self._yuz([k[(-1, -1, 1)], k[(1, -1, 1)], k[(1, 1, 1)], k[(-1, 1, 1)]], (0, 0, 1), renk)

    def silindir(self, merkez, eksen, yaricap, uzunluk, renk, kapak_renk=None, kenar=10, kapaklar=True):
        """Ekseni verilen yönde, kenar sayısı 'kenar' olan prizma (silindir yaklaşımı)."""
        e = np.array(eksen, dtype=float)
        e /= np.linalg.norm(e)
        yardimci = np.array([0, 0, 1.0]) if abs(e[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(e, yardimci)
        u /= np.linalg.norm(u)
        v = np.cross(e, u)
        m = np.array(merkez, dtype=float)
        on, arka = m + e * uzunluk / 2, m - e * uzunluk / 2
        on_i, arka_i = [], []
        for i in range(kenar):
            a = 2 * math.pi * i / kenar
            d = (math.cos(a) * u + math.sin(a) * v) * yaricap
            on_i.append(self._kose(on + d))
            arka_i.append(self._kose(arka + d))
        for i in range(kenar):
            j = (i + 1) % kenar
            a = 2 * math.pi * (i + 0.5) / kenar
            n = math.cos(a) * u + math.sin(a) * v
            self._yuz([arka_i[i], arka_i[j], on_i[j], on_i[i]], n, renk)
        if kapaklar:
            self._yuz(on_i[::-1] if np.dot(np.cross(u, v), e) < 0 else on_i, e, kapak_renk or renk)
            self._yuz(arka_i if np.dot(np.cross(u, v), e) < 0 else arka_i[::-1], -e, kapak_renk or renk)

    def halka(self, merkez, eksen, r_dis, r_ic, renk, kenar=12):
        """Motor koruyucusunun ağız kısmı (iki yüzlü düz halka)."""
        e = np.array(eksen, dtype=float)
        e /= np.linalg.norm(e)
        yardimci = np.array([0, 0, 1.0]) if abs(e[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(e, yardimci)
        u /= np.linalg.norm(u)
        v = np.cross(e, u)
        m = np.array(merkez, dtype=float)
        for i in range(kenar):
            a0, a1 = 2 * math.pi * i / kenar, 2 * math.pi * (i + 1) / kenar
            d0 = math.cos(a0) * u + math.sin(a0) * v
            d1 = math.cos(a1) * u + math.sin(a1) * v
            idx = [self._kose(m + d0 * r_ic), self._kose(m + d0 * r_dis),
                   self._kose(m + d1 * r_dis), self._kose(m + d1 * r_ic)]
            self._yuz(idx, e, renk, cift=True)

    def _kur(self):
        # Yan çerçeve plakaları: içi boş çerçeve (üst, alt, ön, orta ve arka kollar)
        for y in (-0.17, 0.17):
            self.kutu((0.0, y, -0.11), (0.44, 0.016, 0.028), SIYAH)
            self.kutu((0.0, y, 0.108), (0.44, 0.016, 0.028), SIYAH)
            for x in (-0.208, 0.0, 0.208):
                self.kutu((x, y, 0.0), (0.026, 0.016, 0.2), SIYAH)
        # Alt bağlantı çubukları
        for x in (-0.19, 0.19):
            self.kutu((x, 0.0, 0.11), (0.025, 0.33, 0.02), KOYU)
        # Batarya tüpü (altta)
        self.silindir((-0.01, 0.0, 0.075), (1, 0, 0), 0.034, 0.25, BATARYA, KOYU)
        # Elektronik tüpü (ortada), ön kubbe ve kamera
        self.silindir((-0.005, 0.0, -0.01), (1, 0, 0), 0.052, 0.31, TUP, KOYU)
        self.silindir((0.165, 0.0, -0.01), (1, 0, 0), 0.044, 0.025, KUBBE, KUBBE)
        self.silindir((0.18, 0.0, -0.01), (1, 0, 0), 0.016, 0.01, KAMERA, KAMERA, kenar=8)
        # Yüzdürme köpüğü (üstte, iki parça ve ortada kabloların geçtiği boşluk)
        for y in (-0.095, 0.095):
            self.kutu((0.0, y, -0.1), (0.4, 0.13, 0.07), SARI)
        # Ön ışıklar
        for x, y, z in ((0.205, -0.09, -0.03), (0.205, 0.09, -0.03)):
            self.silindir((x, y, z), (1, 0, 0), 0.017, 0.03, KOYU, ISIK, kenar=8)
        # Motorlar
        for ad, mx, my, aci, dikey in A.ITICILER:
            if dikey:
                merkez, eksen = (mx, my, -0.04), (0, 0, 1)
                # motoru plakaya bağlayan kol
                self.kutu((mx, my * 0.86, -0.04), (0.03, abs(my) * 0.3, 0.02), KOYU)
            else:
                a = math.radians(aci)
                merkez, eksen = (mx, my, 0.05), (math.cos(a), math.sin(a), 0)
            self.silindir(merkez, eksen, 0.044, 0.075, MOTOR, HALKA, kenar=12, kapaklar=False)
            e = np.array(eksen, dtype=float)
            for yon in (-1, 1):                                              # koruyucunun iki ağzı
                self.halka(np.array(merkez) + yon * e * 0.0375, e, 0.046, 0.038, HALKA)
            self.silindir(merkez, eksen, 0.014, 0.05, HALKA, HALKA, kenar=8)       # motor gövdesi (göbek)

    # ------------------------------------------------------------ #
    # Pervaneler (her karede yeniden oluşturulur, motor gücüyle döner)
    # ------------------------------------------------------------ #
    def pervaneleri_dondur(self, motor_kuvvetleri, dt):
        for i, f in enumerate(motor_kuvvetleri):
            self.pervane_acisi[i] = (self.pervane_acisi[i] + 30.0 * f / A.ITICI_ILERI_MAX * dt) % (2 * math.pi)

    def _pervane_geometrisi(self):
        koseler, yuzler = [], []
        n0 = len(self.statik_koseler)
        for i, (m, e, u, v) in enumerate(self._pervane_eksen):
            for kanat in range(3):                                  # 3 kanatlı pervane
                a = self.pervane_acisi[i] + kanat * 2 * math.pi / 3 + self._kanat_aci
                noktalar = m + (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v) * self._kanat_r[:, None]
                bas = n0 + len(koseler) * 4
                koseler.append(noktalar)
                yuzler.append(([bas, bas + 1, bas + 2, bas + 3], e, PERVANE, True))
        return np.vstack(koseler), yuzler

    # ------------------------------------------------------------ #
    # Çizim
    # ------------------------------------------------------------ #
    def ciz(self, ekran, x, y, z, psi, izdusum, bakis, sis=None, kenar=True):
        """
        Hesaplar numpy ile topludur; Python döngüsü sadece görünen yüzleri çizer.
        izdusum(K)        : K (n,3) dünya noktaları -> ((n,2) ekran koordinatları, (n,) geçerli mi)
        bakis(merkez, nor): (m,3) yüz merkezleri ve normalleri -> ((m,) görünür mü, (m,) derinlik)
                            derinliği büyük olan önce çizilir (ressam algoritması)
        sis(renk, merkez) : (m,3) renkler ve merkezler -> sisli renkler (isteğe bağlı)
        """
        pk, pyuz = self._pervane_geometrisi()
        c, s = math.cos(psi), math.sin(psi)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
        konum = np.array([x, y, z])
        govde = np.vstack([self.statik_koseler, pk])
        dunya = govde @ R.T + konum

        # yüz özellikleri: statik + pervaneler
        p_idx = [f[0] for f in pyuz]
        merkez_g = np.vstack([self._s_merkez, pk.reshape(-1, 4, 3).mean(axis=1)])
        normal_g = np.vstack([self._s_normal, np.array([f[1] for f in pyuz])])
        renk = np.vstack([self._s_renk, np.array([f[2] for f in pyuz], dtype=float)])
        cift = np.concatenate([self._s_cift, np.ones(len(pyuz), dtype=bool)])
        kenarli = np.concatenate([self._s_kenar, np.zeros(len(pyuz), dtype=bool)])
        indeksler = [f[0] for f in self.statik_yuzler] + p_idx

        merkez = merkez_g @ R.T + konum
        normal = normal_g @ R.T
        gorunur, derinlik = bakis(merkez, normal)
        gorunur = gorunur | cift

        # düz gölgelendirme: ışığa bakan yüz aydınlık, arkası gölgede
        isik = -(normal @ ISIK_YONU)
        isik = np.where(cift, np.abs(isik), isik)
        renk = np.clip(renk * (0.42 + 0.68 * np.clip(isik, 0, None))[:, None], 0, 255)
        if sis is not None:
            renk = sis(renk, merkez)
        renk = renk.astype(int)

        ekran_k, gecerli = izdusum(dunya)
        ekran_k = ekran_k.tolist()
        sira = np.argsort(-derinlik)
        for i in sira[gorunur[sira]]:
            idx = indeksler[i]
            if not gecerli[idx].all():
                continue
            noktalar = [ekran_k[j] for j in idx]
            r = tuple(renk[i])
            pygame.draw.polygon(ekran, r, noktalar)
            if kenar and kenarli[i]:
                pygame.draw.polygon(ekran, (r[0] * 55 // 100, r[1] * 55 // 100, r[2] * 55 // 100), noktalar, 1)

    def dunya_noktasi(self, x, y, z, psi, bx, by, bz):
        c, s = math.cos(psi), math.sin(psi)
        return (x + bx * c - by * s, y + bx * s + by * c, z + bz)

    def ayak_izi(self):
        """Üstten bakınca aracın kapladığı alan (gölge için), gövde ekseninde."""
        return [(0.23, -0.24), (0.23, 0.24), (-0.23, 0.24), (-0.23, -0.24)]
