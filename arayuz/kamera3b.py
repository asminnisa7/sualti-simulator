"""
3B takip kamerası: aracın arkasından ve biraz yukarısından bakan perspektif görünüm.

Yöntem (kütüphanesiz, elle 3B çizim):
  1) Kamera konumu ve bakış yönünden kamera eksenleri (sağ, yukarı, ileri) hesaplanır.
  2) Her 3B nokta kamera eksenlerine izdüşürülür, perspektif bölmesiyle (x/z, y/z) ekrana taşınır.
  3) Kameranın arkasında kalan çizgi ve çokgenler "yakın düzlem"de kırpılır.
  4) Nesneler uzaktan yakına sıralanıp çizilir (ressam algoritması).
  5) Uzaktaki nesnelerin rengi su rengine karışır (sis): su altında görüş mesafesi kısadır.

Dünya ekseni: x havuz boyu, y havuz eni, z aşağı (derinlik).
"""
import math
import random

import numpy as np
import pygame

import ayarlar as A
from . import tema as T

SIS = (12, 52, 82)              # uzaktaki her şeyin karıştığı su rengi
YAKIN = 0.1                     # yakın kırpma düzlemi (m)


def _karistir(renk, hedef, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(renk, hedef))


def _normalize(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return (v[0] / n, v[1] / n, v[2] / n)


def _capraz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


class Kamera3B:
    def __init__(self, model, kabarciklar):
        self.model = model
        self.kabarciklar = kabarciklar
        self.zaman = 0.0
        self.kar = []                    # suda süzülen parçacıklar ("deniz karı")
        self._katman = None
        self.yaw = None                  # kameranın yönü (araca yumuşak gecikmeyle uyar)
        self.gorus_acisi = math.radians(72)
        self.sis_mesafesi = 26.0         # bu mesafede her şey tamamen suya karışır
        self._arka = None
        self._statik_hazirla()

    # ------------------------------------------------------------ #
    # Sabit geometri: taban ızgarası, kulvarlar, duvar fayansları, yüzey.
    # Hiç değişmedikleri için çizgiler bir kez hazırlanır; her karede numpy ile
    # hepsi birden kamera uzayına dönüştürülür (Python döngüsünden ~10 kat hızlı).
    # ------------------------------------------------------------ #
    def _statik_hazirla(self):
        L, W, D = A.HAVUZ_UZUNLUK, A.HAVUZ_GENISLIK, A.MAX_DERINLIK
        bas, son, renk, kalin = [], [], [], []

        def ekle(a, b, r, k=1):
            bas.append(a); son.append(b); renk.append(r); kalin.append(k)

        izgara, fayans, yuzey_r, kulvar = (70, 140, 172), (84, 146, 172), (120, 190, 220), (16, 52, 86)
        for i in range(int(L) + 1):                                  # taban ızgarası
            for j in range(0, int(W), 2):
                ekle((i, j, D), (i, min(j + 2, W), D), izgara)
        for j in range(int(W) + 1):
            for i in range(0, int(L), 2):
                ekle((i, j, D), (min(i + 2, L), j, D), izgara)
        j = 2.5
        while j < W:                                                 # kulvar çizgileri
            for i in range(2, int(L) - 2, 2):
                ekle((i, j, D - 0.01), (i + 2, j, D - 0.01), kulvar, 3)
            j += 2.5
        for x in (0.0, L):                                           # kısa duvarlar
            for s in range(int(W) + 1):
                ekle((x, s, 0), (x, s, D), fayans)
            for d in range(1, int(D)):
                for s in range(0, int(W), 2):
                    ekle((x, s, d), (x, min(s + 2, W), d), fayans)
        for y in (0.0, W):                                           # uzun duvarlar
            for s in range(int(L) + 1):
                ekle((s, y, 0), (s, y, D), fayans)
            for d in range(1, int(D)):
                for s in range(0, int(L), 2):
                    ekle((s, y, d), (min(s + 2, L), y, d), fayans)
        for i in range(0, int(L) + 1, 2):                            # su yüzeyi (aşağıdan)
            for j in range(0, int(W), 3):
                ekle((i, j, 0), (i, min(j + 3, W), 0), yuzey_r)

        self._sa = np.array(bas, dtype=float)
        self._sb = np.array(son, dtype=float)
        self._sr = np.array(renk, dtype=float)
        self._sk = np.array(kalin)
        self._sm = (self._sa + self._sb) / 2                         # orta noktalar (sis için)

        # taban ve duvar dolguları (5 m'lik parçalar)
        self._dolgular = []
        for bx in range(0, int(L), 5):
            for by in range(0, int(W), 5):
                x1, y1 = min(bx + 5, L), min(by + 5, W)
                self._dolgular.append(([(bx, by, D), (x1, by, D), (x1, y1, D), (bx, y1, D)],
                                       (44, 104, 136), ((bx + x1) / 2, (by + y1) / 2, D)))
        for x in (0.0, L):
            for by in range(0, int(W), 5):
                y1 = min(by + 5, W)
                self._dolgular.append(([(x, by, 0), (x, y1, 0), (x, y1, D), (x, by, D)],
                                       (58, 118, 146), (x, (by + y1) / 2, D / 2)))
        for y in (0.0, W):
            for bx in range(0, int(L), 5):
                x1 = min(bx + 5, L)
                self._dolgular.append(([(bx, y, 0), (x1, y, 0), (x1, y, D), (bx, y, D)],
                                       (58, 118, 146), ((bx + x1) / 2, y, D / 2)))

    def _statik_ciz(self, ekran):
        kam = np.array(self.konum)
        # dolgular (uzaktan yakına)
        siralanmis = sorted(self._dolgular, key=lambda d: -math.dist(d[2], self.konum))
        for kose, renk, merkez in siralanmis:
            self._cokgen(ekran, kose, self._sis(renk, merkez))
        # çizgiler: hepsini birden kamera uzayına çevir
        R = np.array([self.sag, self.yukari, self.ileri])
        ca = (self._sa - kam) @ R.T
        cb = (self._sb - kam) @ R.T
        mesafe = np.linalg.norm(self._sm - kam, axis=1)
        gorunur = (mesafe < self.sis_mesafesi) & ((ca[:, 2] > YAKIN) | (cb[:, 2] > YAKIN))
        ca, cb, mesafe = ca[gorunur], cb[gorunur], mesafe[gorunur]
        renk, kalin = self._sr[gorunur], self._sk[gorunur]
        # yakın düzlemde kırp
        arkada_a = ca[:, 2] < YAKIN
        arkada_b = cb[:, 2] < YAKIN
        t = (YAKIN - ca[:, 2]) / np.where(cb[:, 2] - ca[:, 2] == 0, 1e-9, cb[:, 2] - ca[:, 2])
        ara = ca + (cb - ca) * t[:, None]
        ca = np.where(arkada_a[:, None], ara, ca)
        cb = np.where(arkada_b[:, None], ara, cb)
        # perspektif izdüşüm
        cx, cy, f = self.alan.centerx, self.alan.centery, self.odak
        ax = (cx + f * ca[:, 0] / ca[:, 2]).astype(int)
        ay = (cy - f * ca[:, 1] / ca[:, 2]).astype(int)
        bx = (cx + f * cb[:, 0] / cb[:, 2]).astype(int)
        by = (cy - f * cb[:, 1] / cb[:, 2]).astype(int)
        # sis: uzaklaştıkça su rengine karış
        s = np.clip(mesafe / self.sis_mesafesi, 0, 1)[:, None] ** 0.9
        renkler = (renk + (np.array(SIS) - renk) * s).astype(int)
        for x0, y0, x1, y1, (r, g, b), k in zip(ax.tolist(), ay.tolist(), bx.tolist(), by.tolist(),
                                                 renkler.tolist(), kalin.tolist()):
            pygame.draw.line(ekran, (r, g, b), (x0, y0), (x1, y1), k)

    # ------------------------------------------------------------ #
    # Kamera ve izdüşüm
    # ------------------------------------------------------------ #
    def _kamera_kur(self, durum, alan, dt):
        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        if self.yaw is None:
            self.yaw = psi
        fark = (psi - self.yaw + math.pi) % (2 * math.pi) - math.pi
        self.yaw += fark * min(1.0, 3.0 * dt)                    # yumuşak takip
        fx, fy = math.cos(self.yaw), math.sin(self.yaw)
        self.konum = (x - 3.0 * fx, y - 3.0 * fy, max(0.2, z - 1.0))   # arkada ve yukarıda
        hedef = (x + 2.5 * fx, y + 2.5 * fy, z + 0.2)
        self.ileri = _normalize((hedef[0] - self.konum[0], hedef[1] - self.konum[1], hedef[2] - self.konum[2]))
        self.sag = _normalize(_capraz(self.ileri, (0.0, 0.0, -1.0)))   # dünya "yukarısı" = -z
        self.yukari = _capraz(self.sag, self.ileri)
        self.alan = alan
        self.odak = (alan.w / 2) / math.tan(self.gorus_acisi / 2)

    def _kam(self, p):
        """Dünya noktası -> kamera uzayı (sağ, yukarı, ileri)."""
        d = (p[0] - self.konum[0], p[1] - self.konum[1], p[2] - self.konum[2])
        return (d[0] * self.sag[0] + d[1] * self.sag[1] + d[2] * self.sag[2],
                d[0] * self.yukari[0] + d[1] * self.yukari[1] + d[2] * self.yukari[2],
                d[0] * self.ileri[0] + d[1] * self.ileri[1] + d[2] * self.ileri[2])

    def _ekran(self, c):
        """Kamera uzayı -> ekran pikseli (perspektif bölmesi)."""
        return (int(self.alan.centerx + self.odak * c[0] / c[2]),
                int(self.alan.centery - self.odak * c[1] / c[2]))

    def _mesafe(self, p):
        return math.dist(p, self.konum)

    def _cizgi(self, ekran, a, b, renk, kalinlik=1):
        ca, cb = self._kam(a), self._kam(b)
        if ca[2] < YAKIN and cb[2] < YAKIN:
            return
        if ca[2] < YAKIN or cb[2] < YAKIN:                         # yakın düzlemde kırp
            t = (YAKIN - ca[2]) / (cb[2] - ca[2])
            ara = tuple(ca[i] + (cb[i] - ca[i]) * t for i in range(3))
            if ca[2] < YAKIN:
                ca = ara
            else:
                cb = ara
        pygame.draw.line(ekran, renk, self._ekran(ca), self._ekran(cb), kalinlik)

    def _cokgen(self, ekran, noktalar, renk, kalinlik=0):
        """Çokgeni yakın düzlemde kırpar (Sutherland-Hodgman) ve çizer."""
        kamera = [self._kam(p) for p in noktalar]
        kirpilmis = []
        for i in range(len(kamera)):
            a, b = kamera[i], kamera[(i + 1) % len(kamera)]
            a_on, b_on = a[2] >= YAKIN, b[2] >= YAKIN
            if a_on:
                kirpilmis.append(a)
            if a_on != b_on:
                t = (YAKIN - a[2]) / (b[2] - a[2])
                kirpilmis.append(tuple(a[j] + (b[j] - a[j]) * t for j in range(3)))
        if len(kirpilmis) >= 3:
            pygame.draw.polygon(ekran, renk, [self._ekran(c) for c in kirpilmis], kalinlik)

    def _sis(self, renk, p):
        return _karistir(renk, SIS, (self._mesafe(p) / self.sis_mesafesi) ** 0.9)

    # ------------------------------------------------------------ #
    def ciz(self, ekran, alan, durum, iticiler, gorev, otopilot, kestirici, iz, dt, akinti=(0.0, 0.0)):
        self.zaman += dt
        self._kamera_kur(durum, alan, dt)
        ekran.set_clip(alan)
        self._arka_plan(ekran, alan)
        self._statik_ciz(ekran)
        self._isik_huzmeleri(ekran, alan)
        self._kablo(ekran, durum, iz)

        # nesneleri uzaktan yakına sırala (ressam algoritması)
        nesneler = []
        for ex, ey, er in A.ENGELLER:
            nesneler.append((self._mesafe((ex, ey, A.MAX_DERINLIK / 2)), self._sutun, (ex, ey, er)))
        z_tahmin = kestirici.durum()[2]
        for i, k in enumerate(gorev.kapilar):
            mesafe = self._mesafe((k.x, k.y, (k.sig + k.derin) / 2))
            if i < gorev.siradaki and mesafe < 5.0:
                continue                      # geçilmiş ve kameranın dibindeki kapı görüşü kapatmasın
            nesneler.append((mesafe, self._kapi, (i, k, gorev, z_tahmin)))
        nesneler.append((self._mesafe((durum[0], durum[1], durum[2])), self._arac, (durum, iticiler)))
        for _, fonksiyon, veri in sorted(nesneler, key=lambda n: -n[0]):
            fonksiyon(ekran, *veri)
        self._kabarciklar(ekran)
        self._deniz_kari(ekran, akinti, dt)
        self._on_isik_konisi(ekran, alan, durum)
        ekran.set_clip(None)

    # ------------------------------------------------------------ #
    def _arka_plan(self, ekran, alan):
        """Yukarıdan (yüzey tarafı) aşağıya koyulaşan su rengi."""
        if self._arka is None or self._arka.get_size() != (alan.w, alan.h):
            self._arka = pygame.Surface((alan.w, alan.h))
            for i in range(0, alan.h, 4):
                t = i / alan.h
                self._arka.fill(_karistir((44, 120, 160), (6, 26, 44), t), (0, i, alan.w, 4))
        ekran.blit(self._arka, (alan.x, alan.y))

    def _iz(self, ekran, iz):
        nokta = iz[-600::4]
        for a, b in zip(nokta, nokta[1:]):
            self._cizgi(ekran, a, b, self._sis((235, 240, 245), a), 1)

    # ------------------------------------------------------------ #
    def _dikey_kutu(self, ekran, x, y, r, z0, z1, renk):
        """Kameraya dönük dikey dikdörtgen (silindirin görünüşü)."""
        dx, dy = x - self.konum[0], y - self.konum[1]
        n = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / n * r, dx / n * r
        kose = [(x - nx, y - ny, z0), (x + nx, y + ny, z0), (x + nx, y + ny, z1), (x - nx, y - ny, z1)]
        self._cokgen(ekran, kose, renk)
        return kose

    def _sutun(self, ekran, ex, ey, er):
        merkez = (ex, ey, A.MAX_DERINLIK / 2)
        kose = self._dikey_kutu(ekran, ex, ey, er, 0, A.MAX_DERINLIK, self._sis((96, 100, 108), merkez))
        # gölgeli kenar ve ışık şeridi: yuvarlaklık hissi
        koyu = self._sis((52, 56, 64), merkez)
        self._cizgi(ekran, kose[0], kose[3], koyu, 3)
        self._cizgi(ekran, kose[1], kose[2], koyu, 3)
        a = tuple(kose[0][i] * 0.7 + kose[1][i] * 0.3 for i in range(3))
        b = tuple(kose[3][i] * 0.7 + kose[2][i] * 0.3 for i in range(3))
        self._cizgi(ekran, a, b, self._sis((150, 154, 162), merkez), 2)

    def _kapi(self, ekran, i, k, gorev, z_tahmin):
        if i < gorev.siradaki:
            renk = (110, 120, 134)
        elif i == gorev.siradaki and not gorev.bitti:
            renk = T.YESIL if k.sig <= z_tahmin <= k.derin else T.TURUNCU
        else:
            renk = (226, 230, 236)
        merkez = (k.x, k.y, (k.sig + k.derin) / 2)
        renk = self._sis(renk, merkez)
        (x1, y1), (x2, y2) = k.direkler()
        # direkler (tabandan yüzeye); kameranın çok yakınındaki direk görüşü kapatmasın
        for x, y in ((x1, y1), (x2, y2)):
            uzaklik = self._kam((x, y, 2.5))[2]
            if uzaklik > 3.0:
                self._dikey_kutu(ekran, x, y, 0.06, 0, A.MAX_DERINLIK, self._sis((170, 176, 186), (x, y, 2.5)))
            elif uzaklik > 0.5:                     # kameranın çok yakını: görüşü kapatmasın, sadece çizgi
                self._cizgi(ekran, (x, y, 0), (x, y, A.MAX_DERINLIK), (150, 160, 172), 1)
        # geçilecek açıklık: renkli çerçeve
        cerceve = [(x1, y1, k.sig), (x2, y2, k.sig), (x2, y2, k.derin), (x1, y1, k.derin)]
        self._cokgen(ekran, cerceve, renk, 4)
        # numara
        c = self._kam((k.x, k.y, k.sig - 0.35))
        if c[2] > YAKIN:
            boyut = max(11, min(30, int(self.odak * 0.25 / c[2])))
            T.yaz(ekran, str(i + 1), (self._ekran(c)[0], self._ekran(c)[1] - boyut), boyut, renk,
                  kalin=True, hiza="orta")

    def _arac(self, ekran, durum, iticiler):
        R = np.array([self.sag, self.yukari, self.ileri])
        kam = np.array(self.konum)
        cx, cy, f = self.alan.centerx, self.alan.centery, self.odak

        def izdusum(K):                                     # perspektif izdüşüm
            c = (K - kam) @ R.T
            gecerli = c[:, 2] > YAKIN
            z = np.where(gecerli, c[:, 2], 1.0)
            e = np.empty((len(K), 2), dtype=int)
            e[:, 0] = (cx + f * c[:, 0] / z).astype(int)
            e[:, 1] = (cy - f * c[:, 1] / z).astype(int)
            return e, gecerli

        def bakis(merkez, n):
            d = merkez - kam
            return np.einsum("ij,ij->i", n, d) < 0, np.linalg.norm(d, axis=1)

        def sis(renk, merkez):
            t = np.clip(np.linalg.norm(merkez - kam, axis=1) / self.sis_mesafesi, 0, 1)[:, None] ** 0.9
            return renk + (np.array(SIS) - renk) * t

        self.model.ciz(ekran, durum[0], durum[1], durum[2], durum[3], izdusum, bakis, sis=sis)

    # ------------------------------------------------------------ #
    # Efektler
    # ------------------------------------------------------------ #
    def _katman_al(self, alan):
        if self._katman is None or self._katman.get_size() != (alan.w, alan.h):
            self._katman = pygame.Surface((alan.w, alan.h), pygame.SRCALPHA)
        self._katman.fill((0, 0, 0, 0))
        return self._katman

    def _isik_huzmeleri(self, ekran, alan):
        """Yüzeyden süzülen, yavaşça salınan ışık huzmeleri (yüzeye yakınken daha belirgin)."""
        guc = max(0.0, 1.0 - self.konum[2] / A.MAX_DERINLIK)
        if guc < 0.05:
            return
        katman = self._katman_al(alan)
        for i in range(7):
            x = (i + 0.5) * alan.w / 7 + 60 * math.sin(self.zaman * 0.25 + i * 1.7)
            g = 26 + 18 * math.sin(self.zaman * 0.4 + i)
            kayma = 160 + 40 * math.sin(i * 2.1)
            alfa = int((10 + 8 * math.sin(self.zaman * 0.6 + i * 0.9)) * guc) + 4
            pygame.draw.polygon(katman, (190, 235, 255, alfa),
                                [(x - g, 0), (x + g, 0), (x + g * 2.2 + kayma, alan.h * 0.85),
                                 (x - g * 0.4 + kayma, alan.h * 0.85)])
        ekran.blit(katman, (alan.x, alan.y))

    def _on_isik_konisi(self, ekran, alan, durum):
        """Aracın ön ışıklarından suya yayılan ışık konisi."""
        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        katman = self._katman_al(alan)
        cizildi = False
        for bx, by, bz in self.model.on_isiklar:
            for uzunluk, genislik, alfa in ((3.2, 0.9, 16), (2.2, 0.45, 22)):
                tepe = self.model.dunya_noktasi(x, y, z, psi, bx, by, bz)
                sol = self.model.dunya_noktasi(x, y, z, psi, bx + uzunluk, by - genislik, bz + 0.15)
                sag = self.model.dunya_noktasi(x, y, z, psi, bx + uzunluk, by + genislik, bz + 0.15)
                kam = [self._kam(p) for p in (tepe, sol, sag)]
                if min(c[2] for c in kam) < YAKIN:
                    continue
                noktalar = [self._ekran(c) for c in kam]
                pygame.draw.polygon(katman, (255, 244, 205, alfa),
                                    [(px - alan.x, py - alan.y) for px, py in noktalar])
                cizildi = True
            # ışığın kendisi: parlak nokta (sadece ışık kameraya dönükse görünür)
            isik_konumu = self.model.dunya_noktasi(x, y, z, psi, bx + 0.02, by, bz)
            kameraya = (self.konum[0] - isik_konumu[0]) * math.cos(psi) + (self.konum[1] - isik_konumu[1]) * math.sin(psi)
            c = self._kam(isik_konumu)
            if c[2] > YAKIN and kameraya > 0:
                px, py = self._ekran(c)
                r = max(2, int(self.odak * 0.018 / c[2]))
                pygame.draw.circle(katman, (255, 250, 225, 90), (px - alan.x, py - alan.y), r * 3)
                pygame.draw.circle(katman, (255, 252, 235, 230), (px - alan.x, py - alan.y), r)
                cizildi = True
        if cizildi:
            ekran.blit(katman, (alan.x, alan.y))

    def _kabarciklar(self, ekran):
        for k in self.kabarciklar.liste:
            c = self._kam((k[0], k[1], k[2]))
            if c[2] < 0.3:
                continue
            px, py = self._ekran(c)
            if not self.alan.collidepoint(px, py):
                continue
            r = max(1, int(self.odak * 0.008 / c[2]))
            renk = self._sis((215, 240, 255), (k[0], k[1], k[2]))
            pygame.draw.circle(ekran, renk, (px, py), r, 1 if r > 2 else 0)

    def _deniz_kari(self, ekran, akinti, dt):
        """Kameranın çevresinde suda süzülen küçük parçacıklar: derinlik ve hareket hissi verir."""
        kx, ky, kz = self.konum
        kalan = []
        for p in self.kar:
            p[0] += akinti[0] * dt
            p[1] += akinti[1] * dt
            p[2] += 0.02 * dt
            if abs(p[0] - kx) < 7 and abs(p[1] - ky) < 7 and 0.05 < p[2] < A.MAX_DERINLIK and abs(p[2] - kz) < 4:
                kalan.append(p)
        while len(kalan) < 160:
            kalan.append([kx + random.uniform(-7, 7), ky + random.uniform(-7, 7),
                          min(A.MAX_DERINLIK - 0.05, max(0.06, kz + random.uniform(-3, 3)))])
        self.kar = kalan
        for p in self.kar:
            c = self._kam(p)
            if c[2] < 0.4:
                continue
            px, py = self._ekran(c)
            if self.alan.collidepoint(px, py):
                renk = self._sis((205, 230, 240), tuple(p))
                pygame.draw.circle(ekran, renk, (px, py), 2 if c[2] < 2 else 1)

    def _kablo(self, ekran, durum, iz):
        """Aracın arkasından yüzeye uzanan bağlantı kablosu (tether)."""
        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        noktalar = [self.model.dunya_noktasi(x, y, z, psi, -0.22, 0.0, -0.02)]
        gecmis = iz[-400::-8][:40] if len(iz) > 8 else []
        n = max(1, len(gecmis))
        for i, (px, py, pz) in enumerate(gecmis):
            t = (i + 1) / n
            noktalar.append((px, py, pz * (1 - t) - 0.05 * t))   # geriye doğru yüzeye yükselir
        for a, b in zip(noktalar, noktalar[1:]):
            self._cizgi(ekran, a, b, self._sis((236, 196, 60), a), 2)
