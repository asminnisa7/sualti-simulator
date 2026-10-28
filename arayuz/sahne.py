"""
Ana görünüm: havuz, kapılar, engeller, araç, iz, akıntı parçacıkları, mini harita.
Kamera aracı takip eder.
"""
import math
import random

import numpy as np
import pygame
from pygame import gfxdraw

import ayarlar as A
from . import tema as T



YAN_KESIT_Y = 140                      # yan kesit şeridinin yüksekliği (piksel)


class Sahne:
    def __init__(self, rect, model, kabarciklar, kostik):
        self.model = model
        self.kabarciklar = kabarciklar
        self.kostik = kostik
        self.zaman = 0.0
        self.rect = rect
        self.gorus = pygame.Rect(rect.x, rect.y, rect.w, rect.h - YAN_KESIT_Y)    # üstten görünüm
        self.serit = pygame.Rect(rect.x, self.gorus.bottom, rect.w, YAN_KESIT_Y)  # yan kesit
        self.olcek = 100.0              # piksel / metre
        self.kamera = (0.0, 0.0)
        self.iz = []
        self.parcaciklar = []

    # ------------------------------------------------------------ #
    def yakinlastir(self, carpan):
        self.olcek = max(8.0, min(200.0, self.olcek * carpan))

    def izi_sifirla(self):
        self.iz.clear()

    def piksel(self, wx, wy):
        """Dünya koordinatı (m) -> ekran pikseli."""
        return (int(self.gorus.centerx + (wx - self.kamera[0]) * self.olcek),
                int(self.gorus.centery + (wy - self.kamera[1]) * self.olcek))

    def govdeden(self, x, y, psi, bx, by):
        c, s = math.cos(psi), math.sin(psi)
        return self.piksel(x + bx * c - by * s, y + bx * s + by * c)

    # ------------------------------------------------------------ #
    def iz_ekle(self, durum):
        self.iz.append((durum[0], durum[1], durum[2]))
        if len(self.iz) > 3000:
            self.iz.pop(0)

    def ciz(self, ekran, durum, iticiler, gorev, akinti, otopilot, kestirici, kare_suresi):
        self.zaman += kare_suresi
        self.kamera = (durum[0], durum[1])
        ekran.set_clip(self.gorus)             # bu bölgenin dışına taşma
        self._havuz(ekran, durum[2])
        self._parcaciklar(ekran, akinti, kare_suresi)
        self._engeller(ekran)
        self._kapilar(ekran, gorev, kestirici.durum()[2])
        self._iz(ekran)
        self._hayalet(ekran, kestirici.durum())
        self._golge(ekran, durum)
        self._kabarciklar_ust(ekran)
        self._arac(ekran, durum, iticiler, otopilot)
        self._mini_harita(ekran, durum, gorev, kestirici.durum())
        self._olcek_cubugu(ekran)
        self._gorunum_etiketi(ekran, "ÜSTTEN GÖRÜNÜM", "3B kamera")
        self.kamera_rozeti(ekran, kestirici)
        self._mesaj(ekran, gorev)
        ekran.set_clip(None)
        self._yan_kesit(ekran, durum, gorev, otopilot, kestirici)

    # ------------------------------------------------------------ #
    def _havuz(self, ekran, z):
        ekran.fill((52, 58, 66), self.gorus)                         # havuz kenarı (beton)
        k = max(0.45, 1 - z / (A.MAX_DERINLIK * 1.6))               # derinlikte su koyulaşır
        su = (int(18 * k), int(92 * k), int(140 * k))
        x0, y0 = self.piksel(0, 0)
        x1, y1 = self.piksel(A.HAVUZ_UZUNLUK, A.HAVUZ_GENISLIK)
        pygame.draw.rect(ekran, su, (x0, y0, x1 - x0, y1 - y0))

        if self.olcek >= 15:                                        # 1 m'lik ızgara
            ince = (int(28 * k), int(104 * k), int(152 * k))
            for i in range(1, int(A.HAVUZ_UZUNLUK)):
                px = self.piksel(i, 0)[0]
                if self.gorus.left <= px <= self.gorus.right:
                    pygame.draw.line(ekran, ince, (px, y0), (px, y1))
            for j in range(1, int(A.HAVUZ_GENISLIK)):
                py = self.piksel(0, j)[1]
                if self.gorus.top <= py <= self.gorus.bottom:
                    pygame.draw.line(ekran, ince, (x0, py), (x1, py))

        kulvar = (int(13 * k), int(70 * k), int(116 * k))           # taban kulvar çizgileri
        j = 2.5
        while j < A.HAVUZ_GENISLIK:
            pygame.draw.line(ekran, kulvar, self.piksel(2.0, j), self.piksel(A.HAVUZ_UZUNLUK - 2.0, j),
                             max(2, int(0.12 * self.olcek)))
            j += 2.5

        # yüzeyden kırılan ışığın tabanda oluşturduğu hareketli desen
        havuz = pygame.Rect(x0, y0, x1 - x0, y1 - y0).clip(self.gorus)
        if havuz.w > 0 and havuz.h > 0:
            ekran.set_clip(havuz)
            yg, yy = self.gorus.w / 2 / self.olcek, self.gorus.h / 2 / self.olcek
            gorunen = (max(0.0, self.kamera[0] - yg), max(0.0, self.kamera[1] - yy),
                       min(A.HAVUZ_UZUNLUK, self.kamera[0] + yg), min(A.HAVUZ_GENISLIK, self.kamera[1] + yy))
            self.kostik.ciz(ekran, self.piksel, self.olcek, gorunen, self.zaman)
            ekran.set_clip(self.gorus)

        pygame.draw.rect(ekran, (205, 214, 224), (x0, y0, x1 - x0, y1 - y0), 3)
        for i in range(0, int(A.HAVUZ_UZUNLUK) + 1, 5):             # koordinat etiketleri
            px = self.piksel(i, 0)[0]
            if self.gorus.left + 10 <= px <= self.gorus.right - 10 and y0 - 18 > self.gorus.top:
                T.yaz(ekran, f"{i} m", (px, y0 - 18), 11, T.SOLUK, hiza="orta")

    def _parcaciklar(self, ekran, akinti, dt):
        yari_g = self.gorus.w / 2 / self.olcek
        yari_y = self.gorus.h / 2 / self.olcek
        kx, ky = self.kamera
        kalan = []
        for px, py in self.parcaciklar:
            px += akinti[0] * dt + random.uniform(-0.002, 0.002)
            py += akinti[1] * dt + random.uniform(-0.002, 0.002)
            if abs(px - kx) < yari_g and abs(py - ky) < yari_y and \
                    0 < px < A.HAVUZ_UZUNLUK and 0 < py < A.HAVUZ_GENISLIK:
                kalan.append((px, py))
        deneme = 0
        while len(kalan) < 130 and deneme < 300:
            deneme += 1
            px = kx + random.uniform(-yari_g, yari_g)
            py = ky + random.uniform(-yari_y, yari_y)
            if 0 < px < A.HAVUZ_UZUNLUK and 0 < py < A.HAVUZ_GENISLIK:
                kalan.append((px, py))
        self.parcaciklar = kalan
        for px, py in self.parcaciklar:
            pygame.draw.circle(ekran, (120, 178, 218), self.piksel(px, py), 1)

    def _engeller(self, ekran):
        for ex, ey, er in A.ENGELLER:
            m = self.piksel(ex, ey)
            r = max(3, int(er * self.olcek))
            golge = max(2, r // 4)
            pygame.draw.circle(ekran, (8, 30, 48), (m[0] + golge, m[1] + golge), r)       # gölge
            gfxdraw.filled_circle(ekran, m[0], m[1], r, (88, 92, 100))
            gfxdraw.filled_circle(ekran, m[0] - r // 4, m[1] - r // 4, max(1, r * 2 // 3), (112, 116, 124))
            gfxdraw.aacircle(ekran, m[0], m[1], r, (40, 42, 48))

    def _kapilar(self, ekran, gorev, z_tahmin):
        for i, k in enumerate(gorev.kapilar):
            if i < gorev.siradaki:
                renk = (96, 108, 122)                                   # geçildi
            elif i == gorev.siradaki and not gorev.bitti:
                renk = T.YESIL if k.sig <= z_tahmin <= k.derin else T.TURUNCU
            else:
                renk = (220, 226, 232)
            d1, d2 = k.direkler()
            p1, p2 = self.piksel(*d1), self.piksel(*d2)
            T.kesikli_cizgi(ekran, renk, p1, p2, 8, 5, 2)
            r = max(4, int(0.12 * self.olcek))
            for p in (p1, p2):
                gfxdraw.filled_circle(ekran, p[0], p[1], r, renk)
                gfxdraw.aacircle(ekran, p[0], p[1], r, (20, 20, 20))
            a = self.piksel(k.x - 0.7 * k.dx, k.y - 0.7 * k.dy)
            b = self.piksel(k.x + 0.7 * k.dx, k.y + 0.7 * k.dy)
            T.ok(ekran, a, b, renk, 2)
            # etiket kutusu
            etiket = f"{i + 1}   {k.sig:.1f}–{k.derin:.1f} m"
            g = T.metin_genisligi(etiket, 12, kalin=True) + 14
            kutu = pygame.Rect(p2[0] + 8, p2[1] - 11, g, 22)
            T.yari_saydam(ekran, kutu, (0, 0, 0), 150, 11)
            T.yaz(ekran, etiket, (kutu.x + 7, kutu.y + 3), 12, renk, kalin=True)

    def _iz(self, ekran):
        if len(self.iz) < 2:
            return
        noktalar = [self.piksel(x, y) for x, y, _ in self.iz]
        parca = max(2, len(noktalar) // 6)
        for i in range(0, len(noktalar) - 1, parca):          # eski kısımlar daha soluk
            dilim = noktalar[i:i + parca + 1]
            if len(dilim) >= 2:
                parlaklik = 90 + int(165 * (i + parca) / len(noktalar))
                parlaklik = min(255, parlaklik)
                pygame.draw.lines(ekran, (parlaklik, parlaklik, parlaklik), False, dilim, 1)

    def _hayalet(self, ekran, t):
        """Yazılımın aracı nerede sandığı (ölü hesap tahmini)."""
        nokta = [self.govdeden(t[0], t[1], t[3], bx, by) for bx, by in self.model.ayak_izi()]
        pygame.draw.polygon(ekran, T.HAYALET, nokta, 1)

    def _golge(self, ekran, durum):
        """Aracın havuz tabanına düşen gölgesi: araç tabandan uzaklaştıkça kayar ve soluklaşır."""
        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        yukseklik = A.MAX_DERINLIK - z
        ox, oy = 0.35 * 0.25 * yukseklik, -0.25 * 0.25 * yukseklik
        noktalar = [self.govdeden(x + ox, y + oy, psi, bx, by) for bx, by in self.model.ayak_izi()]
        xs, ys = [p[0] for p in noktalar], [p[1] for p in noktalar]
        sx, sy = min(xs) - 2, min(ys) - 2
        yuzey = pygame.Surface((max(xs) - sx + 4, max(ys) - sy + 4), pygame.SRCALPHA)
        alfa = int(110 * (1 - 0.7 * yukseklik / A.MAX_DERINLIK))
        pygame.draw.polygon(yuzey, (0, 12, 24, alfa), [(px - sx, py - sy) for px, py in noktalar])
        ekran.blit(yuzey, (sx, sy))

    def _kabarciklar_ust(self, ekran):
        for k in self.kabarciklar.liste:
            omur = k[6] / k[7]
            r = max(1, int(0.012 * self.olcek * (1.4 - 0.6 * omur)))
            p = self.piksel(k[0], k[1])
            parlak = int(150 + 90 * omur)
            pygame.draw.circle(ekran, (parlak, min(255, parlak + 20), 255), p, r, 1)

    def _arac(self, ekran, durum, iticiler, otopilot):
        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        gx, gy, o = self.gorus.centerx, self.gorus.centery, self.olcek
        kx, ky = self.kamera

        def izdusum(K):                                     # yukarıdan dik izdüşüm
            e = np.empty((len(K), 2), dtype=int)
            e[:, 0] = (gx + (K[:, 0] - kx) * o).astype(int)
            e[:, 1] = (gy + (K[:, 1] - ky) * o).astype(int)
            return e, np.ones(len(K), dtype=bool)

        self.model.ciz(ekran, x, y, z, psi, izdusum,
                       bakis=lambda merkez, n: (n[:, 2] < 0, merkez[:, 2]),     # yukarıdan bakış
                       kenar=self.olcek >= 60)
        # yere göre hız vektörü
        c, s = math.cos(psi), math.sin(psi)
        vx, vy = c * durum[4] - s * durum[5], s * durum[4] + c * durum[5]
        if math.hypot(vx, vy) > 0.05:
            T.ok(ekran, self.piksel(x, y), self.piksel(x + vx, y + vy), (90, 255, 140), 2)
        # hedef yön (otopilot)
        if otopilot.bas_acik:
            h = otopilot.hedef_bas
            T.kesikli_cizgi(ekran, T.SARI, self.piksel(x, y),
                            self.piksel(x + 1.6 * math.cos(h), y + 1.6 * math.sin(h)), 5, 4, 1)

    def _mini_harita(self, ekran, durum, gorev, t, alan=None, kamera_alani=True):
        alan = alan or self.gorus
        g = 240
        h = int(g * A.HAVUZ_GENISLIK / A.HAVUZ_UZUNLUK)
        kutu = pygame.Rect(alan.x + 12, alan.bottom - h - 40, g + 16, h + 30)
        T.yari_saydam(ekran, kutu, (5, 10, 18), 190, 10)
        T.yaz(ekran, "HARİTA", (kutu.x + 8, kutu.y + 5), 11, T.SOLUK, kalin=True)
        mx, my = kutu.x + 8, kutu.y + 22
        o = g / A.HAVUZ_UZUNLUK

        def m(px, py):
            return (int(mx + px * o), int(my + py * o))

        pygame.draw.rect(ekran, (22, 84, 128), (mx, my, g, h))
        pygame.draw.rect(ekran, (180, 190, 200), (mx, my, g, h), 1)
        for ex, ey, er in A.ENGELLER:
            pygame.draw.circle(ekran, (100, 104, 112), m(ex, ey), max(2, int(er * o)))
        for i, k in enumerate(gorev.kapilar):
            renk = (96, 108, 122) if i < gorev.siradaki else \
                (T.YESIL if i == gorev.siradaki and not gorev.bitti else (220, 226, 232))
            d1, d2 = k.direkler()
            pygame.draw.line(ekran, renk, m(*d1), m(*d2), 2)
        if kamera_alani:                                   # üstten görünümün gördüğü alan
            yg, yy = self.gorus.w / 2 / self.olcek, self.gorus.h / 2 / self.olcek
            a, b = m(durum[0] - yg, durum[1] - yy), m(durum[0] + yg, durum[1] + yy)
            ekran.set_clip(pygame.Rect(mx, my, g, h))
            pygame.draw.rect(ekran, (255, 255, 255), (a[0], a[1], b[0] - a[0], b[1] - a[1]), 1)
            ekran.set_clip(alan)
        else:                                              # 3B kamera: bakış yönü oku
            c, s_ = math.cos(durum[3]), math.sin(durum[3])
            T.ok(ekran, m(durum[0], durum[1]), m(durum[0] + 4 * c, durum[1] + 4 * s_), T.YAZI, 1, 5)
        pygame.draw.circle(ekran, T.HAYALET, m(t[0], t[1]), 5, 1)
        pygame.draw.circle(ekran, T.ARAC, m(durum[0], durum[1]), 3)

    def _olcek_cubugu(self, ekran):
        metre = 1 if self.olcek >= 20 else 5
        uz = int(metre * self.olcek)
        x1 = self.gorus.right - 20
        x0, y0 = x1 - uz, self.gorus.bottom - 24
        pygame.draw.line(ekran, T.YAZI, (x0, y0), (x1, y0), 2)
        pygame.draw.line(ekran, T.YAZI, (x0, y0 - 5), (x0, y0 + 5), 2)
        pygame.draw.line(ekran, T.YAZI, (x1, y0 - 5), (x1, y0 + 5), 2)
        T.yaz(ekran, f"{metre} m", ((x0 + x1) // 2, y0 - 20), 12, T.YAZI, hiza="orta")

    def _gorunum_etiketi(self, ekran, ad, diger, alan=None):
        alan = alan or self.gorus
        kutu = pygame.Rect(alan.x + 12, alan.y + 12, 0, 28)
        kutu.w = T.metin_genisligi(ad, 12, kalin=True) + T.metin_genisligi(diger, 12) + 64
        T.yari_saydam(ekran, kutu, (5, 10, 18), 180, 14)
        x = kutu.x + 10 + T.yaz(ekran, ad, (kutu.x + 10, kutu.y + 6), 12, T.YAZI, kalin=True) + 10
        x += T.tus(ekran, x, kutu.y + 4, "V", 11) + 6
        T.yaz(ekran, diger, (x, kutu.y + 6), 12, T.SOLUK)

    def kamera_rozeti(self, ekran, kestirici, alan=None):
        """Kapı kamerası sıradaki kapıyı görüp konumu düzeltirken gösterilen etiket."""
        if kestirici.kapi_goruldu is None:
            return
        alan = alan or self.gorus
        metin = f"KAMERA: kapı {kestirici.kapi_goruldu + 1} görüldü · konum düzeltiliyor"
        kutu = pygame.Rect(alan.x + 12, alan.y + 46, T.metin_genisligi(metin, 12, kalin=True) + 24, 24)
        T.yari_saydam(ekran, kutu, (10, 40, 22), 200, 12)
        pygame.draw.circle(ekran, T.YESIL, (kutu.x + 11, kutu.centery), 4)
        T.yaz(ekran, metin, (kutu.x + 19, kutu.y + 4), 12, T.YESIL, kalin=True)

    def _mesaj(self, ekran, gorev, alan=None):
        alan = alan or self.gorus
        if gorev.mesaj and gorev.mesaj_suresi > 0:
            g = T.metin_genisligi(gorev.mesaj, 20, kalin=True) + 40
            kutu = pygame.Rect(alan.centerx - g // 2, alan.y + 16, g, 40)
            T.yari_saydam(ekran, kutu, (0, 0, 0), 200, 20)
            T.yaz(ekran, gorev.mesaj, (kutu.centerx, kutu.y + 7), 20, T.YAZI, kalin=True, hiza="orta")

    # ------------------------------------------------------------ #
    def _yan_kesit(self, ekran, durum, gorev, otopilot, kestirici):
        """Havuzu aracın yanından görür: yatay eksen aracın önü, dikey eksen derinlik."""
        r = self.serit
        ekran.set_clip(r)
        ust, alt = r.y + 26, r.bottom - 12                 # su yüzeyi ve taban (piksel)
        geri, ileri = -3.0, 15.0                           # görünen aralık (m)
        sol = r.x + 46
        hx = (r.right - 10 - sol) / (ileri - geri)         # piksel / metre (yatay)
        hz = (alt - ust) / A.MAX_DERINLIK                  # piksel / metre (dikey)

        def p(s_, z):
            return (int(sol + (s_ - geri) * hx), int(ust + z * hz))

        # su: derinlikle koyulaşan bantlar
        ekran.fill((14, 21, 32), r)
        bant = 8
        for i in range(bant):
            k = 1 - 0.55 * i / bant
            y0 = ust + (alt - ust) * i // bant
            y1 = ust + (alt - ust) * (i + 1) // bant
            pygame.draw.rect(ekran, (int(24 * k), int(100 * k), int(150 * k)), (sol, y0, r.right - 10 - sol, y1 - y0 + 1))
        dalga = [(px, int(ust + 1.5 * math.sin(px * 0.05 + self.zaman * 2.0)))          # dalgalı yüzey
                 for px in range(sol, r.right - 10, 6)]
        pygame.draw.lines(ekran, (150, 210, 240), False, dalga, 2)
        pygame.draw.rect(ekran, (70, 82, 92), (sol, alt, r.right - 10 - sol, 4))              # taban

        x, y, z, psi = durum[0], durum[1], durum[2], durum[3]
        fx, fy = math.cos(psi), math.sin(psi)                  # aracın önü
        sx, sy = -fy, fx                                       # aracın sağı

        def izdusum(px, py):
            dx, dy = px - x, py - y
            return dx * fx + dy * fy, dx * sx + dy * sy        # (önde ne kadar, yanda ne kadar)

        su = (20, 80, 120)

        def soldur(renk, yan, sinir):
            t = min(1.0, abs(yan) / sinir)
            return tuple(int(c + (s0 - c) * t * 0.85) for c, s0 in zip(renk, su))

        # engeller (aracın 4 m yakınındakiler, uzaklaştıkça soluk)
        for ex, ey, er in A.ENGELLER:
            on, yan = izdusum(ex, ey)
            if abs(yan) < 3 + er and geri - er < on < ileri + er:
                renk = soldur((110, 114, 122), yan, 3 + er)
                x0, x1 = p(on - er, 0)[0], p(on + er, 0)[0]
                pygame.draw.rect(ekran, renk, (x0, ust, max(2, x1 - x0), alt - ust))

        # kapılar: geçilecek açıklık (derinlik aralığı) renkli çerçeve olarak
        for i, k in enumerate(gorev.kapilar):
            on, yan = izdusum(k.x, k.y)
            if abs(yan) > 6 or not (geri < on < ileri):
                continue
            if i < gorev.siradaki:
                renk = (96, 108, 122)
            elif i == gorev.siradaki and not gorev.bitti:
                renk = T.YESIL if k.sig <= kestirici.durum()[2] <= k.derin else T.TURUNCU
            else:
                renk = (220, 226, 232)
            renk = soldur(renk, yan, 8)
            gx = p(on, 0)[0]
            pygame.draw.line(ekran, (90, 100, 112), (gx, ust), (gx, alt), 1)               # direk
            a, b = p(on, k.sig)[1], p(on, k.derin)[1]
            pygame.draw.rect(ekran, renk, (gx - 4, a, 8, b - a), 2, border_radius=2)        # açıklık
            T.yaz(ekran, str(i + 1), (gx, ust - 18), 12, renk, kalin=True, hiza="orta")

        # otopilot hedef derinliği
        if otopilot.derinlik_acik:
            hy = p(0, otopilot.hedef_derinlik)[1]
            T.kesikli_cizgi(ekran, T.SARI, (sol, hy), (r.right - 10, hy), 6, 5, 1)

        # kabarcıklar
        for kb in self.kabarciklar.liste:
            on, yan = izdusum(kb[0], kb[1])
            if geri < on < ileri:
                pygame.draw.circle(ekran, (190, 225, 245), p(on, kb[2]), 1)

        # araç (yandan, gerçek oranlarda) ve tahmini derinliği
        ax, ay = p(0, z)
        k = hx

        def yandan(K):                                      # yandan dik izdüşüm
            e = np.empty((len(K), 2), dtype=int)
            e[:, 0] = (ax + ((K[:, 0] - x) * fx + (K[:, 1] - y) * fy) * k).astype(int)
            e[:, 1] = (ay + (K[:, 2] - z) * k).astype(int)
            return e, np.ones(len(K), dtype=bool)

        self.model.ciz(ekran, x, y, z, psi, yandan,
                       bakis=lambda merkez, n: (n[:, 0] * sx + n[:, 1] * sy < 0,
                                                (merkez[:, 0] - x) * sx + (merkez[:, 1] - y) * sy),
                       kenar=False)
        ty = p(0, kestirici.durum()[2])[1]
        uz, yk = int(0.46 * k), int(0.26 * k)
        pygame.draw.rect(ekran, T.HAYALET, (ax - uz // 2 - 3, ty - yk // 2 - 3, uz + 6, yk + 6), 1)

        for d in range(0, int(A.MAX_DERINLIK) + 1):
            y = p(0, d)[1]
            T.yaz(ekran, f"{d} m", (sol - 6, y - 7), 11, T.SOLUK, hiza="sag")
        for m in range(0, int(ileri) + 1, 5):
            ex = p(m, 0)[0]
            pygame.draw.line(ekran, (90, 120, 150), (ex, alt - 4), (ex, alt), 1)
            if m > 0:
                T.yaz(ekran, f"{m} m", (ex, alt - 16), 10, T.SOLUK, hiza="orta")
        T.yaz(ekran, "YAN KESİT", (r.x + 12, r.y + 5), 11, T.SOLUK, kalin=True)
        T.yaz(ekran, "aracın önü  →", (r.right - 14, r.y + 5), 11, T.SOLUK, hiza="sag")
        pygame.draw.line(ekran, T.KART_KENAR, (r.x, r.y), (r.right, r.y))
        ekran.set_clip(None)
