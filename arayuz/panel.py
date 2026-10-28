"""
Gösterge paneli: üst durum çubuğu ve sağdaki kartlar
(görev, navigasyon, derinlik, motorlar, batarya).
"""
import math
from collections import deque

import pygame
from pygame import gfxdraw

import ayarlar as A
from ortam import sure_yazisi
from . import tema as T


# ------------------------------------------------------------------ #
# Üst durum çubuğu
# ------------------------------------------------------------------ #
def ust_cubuk(ekran, rect, otopilot, akinti, akinti_acik, turbulans, sensorler, guc):
    ekran.fill((14, 21, 32), rect)
    pygame.draw.line(ekran, T.KART_KENAR, (rect.x, rect.bottom - 1), (rect.right, rect.bottom - 1))
    T.yaz(ekran, "ROV SİMÜLATÖRÜ", (rect.x + 14, rect.y + 11), 16, T.YAZI, kalin=True)

    x, y = rect.x + 175, rect.y + 9
    bosluk = 8
    if otopilot.bas_acik:
        metin = f"YÖN SABİT  {math.degrees(otopilot.hedef_bas) % 360:.0f}°"
    else:
        metin = "YÖN SABİT"
    x += T.rozet(ekran, x, y, metin, "H", otopilot.bas_acik) + bosluk
    if otopilot.derinlik_acik:
        metin = f"DERİNLİK SABİT  {otopilot.hedef_derinlik:.2f} m"
    else:
        metin = "DERİNLİK SABİT"
    x += T.rozet(ekran, x, y, metin, "J", otopilot.derinlik_acik) + bosluk
    hiz = math.hypot(*akinti)
    x += T.rozet(ekran, x, y, f"AKINTI  {hiz:.2f} m/s" if akinti_acik else "AKINTI",
                 "C", akinti_acik, T.VURGU) + bosluk
    x += T.rozet(ekran, x, y, "TÜRBÜLANS", "T", akinti_acik and turbulans, T.VURGU) + bosluk
    x += T.rozet(ekran, x, y, "SENSÖR: İDEAL" if sensorler.ideal else "SENSÖR: GERÇEKÇİ",
                 "N", True, T.SARI if sensorler.ideal else T.VURGU) + bosluk
    T.rozet(ekran, x, y, f"GÜÇ %{int(guc * 100)}", "1-3", True, T.TURUNCU)

    T.yaz(ekran, "Yardım", (rect.right - 14, rect.y + 13), 13, T.SOLUK, hiza="sag")
    T.tus(ekran, rect.right - 14 - T.metin_genisligi("Yardım", 13) - 42, rect.y + 11, "TAB")


# ------------------------------------------------------------------ #
# Sağ panel
# ------------------------------------------------------------------ #
class Panel:
    def __init__(self, rect):
        self.rect = rect
        self.gecmis = deque()          # (zaman, gerçek z, Kalman z, ölçüm z, hedef z ya da None)
        self.zaman = 0.0
        self._son_kayit = -1.0
        x, w = rect.x + 8, rect.w - 16
        y = rect.y + 8
        boylar = [84, 172, 150, 128, 104]
        self.kartlar = []
        for b in boylar:
            self.kartlar.append(pygame.Rect(x, y, w, b))
            y += b + 6

    def sifirla(self):
        self.gecmis.clear()
        self.zaman = 0.0
        self._son_kayit = -1.0

    def ciz(self, ekran, durum, iticiler, gorev, akinti, akinti_acik, otopilot, batarya,
            kestirici, kare_suresi):
        self.zaman += kare_suresi
        t = kestirici.durum()
        if self.zaman - self._son_kayit >= 0.1:
            hedef = otopilot.hedef_derinlik if otopilot.derinlik_acik else None
            self.gecmis.append((self.zaman, durum[2], t[2], kestirici.son_derinlik_olcumu, hedef))
            self._son_kayit = self.zaman
        while self.gecmis and self.gecmis[0][0] < self.zaman - 30.0:
            self.gecmis.popleft()

        ekran.fill(T.ARKA, self.rect)
        k = self.kartlar
        self._gorev(ekran, k[0], gorev)
        self._navigasyon(ekran, k[1], durum, t, akinti, akinti_acik, otopilot)
        self._derinlik(ekran, k[2], durum, t, gorev, kestirici)
        self._motorlar(ekran, k[3], iticiler)
        self._batarya(ekran, k[4], batarya)

    # ------------------------------------------------------------ #
    def _gorev(self, ekran, r, gorev):
        T.kart(ekran, r, "GÖREV", f"Süre  {sure_yazisi(gorev.sure)}")
        n = len(gorev.kapilar)
        if gorev.bitti:
            T.yaz(ekran, "TAMAMLANDI", (r.x + 12, r.y + 26), 22, T.YESIL, kalin=True)
        else:
            T.yaz(ekran, f"Kapı {gorev.siradaki + 1}", (r.x + 12, r.y + 24), 22, T.YAZI, kalin=True)
            k = gorev.kapilar[gorev.siradaki]
            T.yaz(ekran, f"/ {n}    derinlik {k.sig:.1f}–{k.derin:.1f} m", (r.x + 96, r.y + 32), 13, T.SOLUK)
        renk = T.KIRMIZI if gorev.carpisma_sayisi else T.SOLUK
        T.yaz(ekran, f"Çarpışma  {gorev.carpisma_sayisi}", (r.right - 12, r.y + 32), 13, renk,
              kalin=bool(gorev.carpisma_sayisi), hiza="sag")
        # ilerleme çubuğu: her kapı bir parça
        g = (r.w - 24 - (n - 1) * 4) / n
        for i in range(n):
            px = int(r.x + 12 + i * (g + 4))
            if i < gorev.siradaki:
                renk = T.YESIL
            elif i == gorev.siradaki and not gorev.bitti:
                renk = T.SARI
            else:
                renk = T.KART_KENAR
            pygame.draw.rect(ekran, renk, (px, r.bottom - 18, int(g), 8), border_radius=4)

    # ------------------------------------------------------------ #
    def _navigasyon(self, ekran, r, durum, t, akinti, akinti_acik, otopilot):
        T.kart(ekran, r, "NAVİGASYON")
        cx, cy, R = r.x + 82, r.y + 102, 60
        bas = round(math.degrees(t[3]), 1) % 360   # gösterge, aracın bildiği (tahmini) değeri gösterir

        gfxdraw.filled_circle(ekran, cx, cy, R, (12, 20, 31))
        gfxdraw.aacircle(ekran, cx, cy, R, T.KART_KENAR)

        def nokta(aci_derece, yaricap):
            """Baş-yukarı pusula: aracın baktığı yön her zaman tepede."""
            a = math.radians(aci_derece - bas)
            return (cx + yaricap * math.sin(a), cy - yaricap * math.cos(a))

        for d in range(0, 360, 10):
            uzun = d % 30 == 0
            p1 = nokta(d, R - 2)
            p2 = nokta(d, R - (10 if uzun else 5))
            pygame.draw.line(ekran, T.YAZI if uzun else T.SONUK,
                             (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), 2 if uzun else 1)
            if d % 90 == 0:
                p = nokta(d, R - 21)
                T.yaz(ekran, str(d), (p[0], p[1] - 8), 12, T.YAZI, kalin=True, hiza="orta")
        # hedef yön işareti
        if otopilot.bas_acik:
            hb = math.degrees(otopilot.hedef_bas)
            p, a, b = nokta(hb, R - 1), nokta(hb - 5, R + 9), nokta(hb + 5, R + 9)
            pygame.draw.polygon(ekran, T.SARI, [(int(p[0]), int(p[1])), (int(a[0]), int(a[1])),
                                                (int(b[0]), int(b[1]))])
        # akıntı oku
        if akinti_acik and math.hypot(*akinti) > 0.01:
            ad = math.degrees(math.atan2(akinti[1], akinti[0]))
            T.ok(ekran, nokta(ad + 180, 26), nokta(ad, 26), T.VURGU, 2, 7)
        # sabit araç simgesi ve baş çizgisi
        pygame.draw.polygon(ekran, T.ARAC, [(cx, cy - 12), (cx - 7, cy + 8), (cx, cy + 4), (cx + 7, cy + 8)])
        pygame.draw.polygon(ekran, T.ARAC, [(cx, cy - R + 1), (cx - 6, cy - R - 8), (cx + 6, cy - R - 8)])

        # sağ taraf: sayısal değerler
        x0 = r.x + 162
        T.yaz(ekran, f"{bas:05.1f}°", (x0, r.y + 22), 26, T.YAZI, kalin=True, mono=True)
        hiz = math.hypot(durum[4], durum[5])
        kayma = math.degrees(math.atan2(durum[5], durum[4])) if hiz > 0.2 else 0.0
        hata = math.hypot(t[0] - durum[0], t[1] - durum[1])
        satirlar = [
            ("Hız", f"{hiz:4.2f} m/s"),
            ("Dönüş", f"{math.degrees(durum[7]):+5.0f} °/s"),
            ("Savrulma", f"{kayma:+5.0f}°"),
            ("Akıntı", f"{math.hypot(*akinti):4.2f} m/s" if akinti_acik else "yok"),
            ("Konum hatası", f"{hata:4.2f} m"),
        ]
        for i, (ad, deger) in enumerate(satirlar):
            yy = r.y + 62 + i * 20
            T.yaz(ekran, ad, (x0, yy), 13, T.SOLUK)
            T.yaz(ekran, deger, (r.right - 12, yy), 13, T.YAZI, mono=True, hiza="sag")

    # ------------------------------------------------------------ #
    def _derinlik(self, ekran, r, durum, t, gorev, kestirici):
        T.kart(ekran, r, "DERİNLİK", "son 30 s")
        T.yaz(ekran, f"{t[2]:.2f} m", (r.x + 12, r.y + 24), 22, T.YAZI, kalin=True, mono=True)
        T.yaz(ekran, f"ölçüm {kestirici.son_derinlik_olcumu:.2f}   gerçek {durum[2]:.2f}   "
                     f"dikey {t[6]:+.2f} m/s", (r.x + 112, r.y + 31), 12, T.SOLUK)

        g = pygame.Rect(r.x + 40, r.y + 56, r.w - 52, r.h - 66)
        pygame.draw.rect(ekran, (12, 20, 31), g, border_radius=4)
        if len(self.gecmis) < 2:
            return
        t1 = self.gecmis[-1][0]
        t0 = t1 - 30.0
        degerler = [h[1] for h in self.gecmis] + [h[2] for h in self.gecmis]
        degerler += [h[4] for h in self.gecmis if h[4] is not None]
        if not gorev.bitti:
            k = gorev.kapilar[gorev.siradaki]
            degerler += [k.sig, k.derin]
        z0 = max(0.0, min(degerler) - 0.3)
        z1 = min(A.MAX_DERINLIK, max(degerler) + 0.3)
        if z1 - z0 < 1.0:
            z1 = z0 + 1.0

        def p(zaman, z):
            return (int(g.x + (zaman - t0) / 30.0 * g.w),
                    int(g.y + (z - z0) / (z1 - z0) * g.h))

        # sıradaki kapının derinlik aralığı (yeşil bant)
        if not gorev.bitti:
            k = gorev.kapilar[gorev.siradaki]
            ust, alt = p(t0, max(z0, k.sig))[1], p(t0, min(z1, k.derin))[1]
            if alt > ust:
                T.yari_saydam(ekran, pygame.Rect(g.x, ust, g.w, alt - ust), T.YESIL, 40, 0)
        for i in range(5):                                       # ızgara ve eksen yazıları
            z = z0 + i * (z1 - z0) / 4
            yy = p(t0, z)[1]
            pygame.draw.line(ekran, (30, 42, 58), (g.x, yy), (g.right, yy))
            T.yaz(ekran, f"{z:.1f}", (g.x - 6, yy - 7), 11, T.SOLUK, hiza="sag")

        ekran.set_clip(g)
        for h in self.gecmis:                                    # ölçümler (gri noktalar)
            pygame.draw.circle(ekran, (90, 100, 116), p(h[0], h[3]), 1)
        hedef = [p(h[0], h[4]) for h in self.gecmis if h[4] is not None]
        if len(hedef) > 1:
            pygame.draw.lines(ekran, T.SARI, False, hedef, 1)
        pygame.draw.lines(ekran, T.VURGU, False, [p(h[0], h[1]) for h in self.gecmis], 2)
        pygame.draw.lines(ekran, (255, 110, 110), False, [p(h[0], h[2]) for h in self.gecmis], 1)
        ekran.set_clip(None)
        # açıklama
        lx = g.right - 150
        for i, (ad, renk) in enumerate((("gerçek", T.VURGU), ("Kalman", (255, 110, 110)), ("hedef", T.SARI))):
            pygame.draw.line(ekran, renk, (lx + i * 52, g.y + 9), (lx + i * 52 + 10, g.y + 9), 2)
            T.yaz(ekran, ad, (lx + i * 52 + 13, g.y + 2), 11, T.SOLUK)

    # ------------------------------------------------------------ #
    def _motorlar(self, ekran, r, iticiler):
        T.kart(ekran, r, "MOTORLAR")
        # araç şeması: burun yukarıda
        cx, cy, k = r.x + 62, r.y + 72, 120.0

        def s(bx, by):
            return (int(cx + by * k), int(cy - bx * k))

        govde = [s(bx, by) for bx, by in [(0.25, -0.15), (0.31, 0.0), (0.25, 0.15), (-0.25, 0.15), (-0.25, -0.15)]]
        gfxdraw.filled_polygon(ekran, govde, (60, 54, 30))
        gfxdraw.aapolygon(ekran, govde, T.ARAC)
        for (ad, mx, my, aci, dikey), f in zip(A.ITICILER, iticiler.f):
            m = s(mx, my)
            renk = T.ILERI if f >= 0 else T.GERI
            oran = min(1.0, abs(f) / A.ITICI_ILERI_MAX)
            if dikey:
                pygame.draw.circle(ekran, (30, 40, 56), m, 9)
                pygame.draw.circle(ekran, renk if oran > 0.02 else T.SONUK, m, 9, 2)
                if oran > 0.02:                                  # ▼ dalma itkisi, ▲ çıkma itkisi
                    yon = 1 if f > 0 else -1
                    pygame.draw.polygon(ekran, renk, [(m[0] - 5, m[1] - 3 * yon), (m[0] + 5, m[1] - 3 * yon),
                                                      (m[0], m[1] + 4 * yon)])
            else:
                pygame.draw.circle(ekran, (30, 40, 56), m, 6)
                pygame.draw.circle(ekran, T.SONUK, m, 6, 1)
                if oran > 0.02:
                    a = math.radians(aci)
                    yon = 1 if f > 0 else -1
                    uc = (m[0] + yon * math.sin(a) * (8 + 26 * oran), m[1] - yon * math.cos(a) * (8 + 26 * oran))
                    T.ok(ekran, m, uc, renk, 2, 6)
        # çubuklar
        x0, cg = r.x + 140, r.w - 140 - 58
        for i, ((ad, *_), f) in enumerate(zip(A.ITICILER, iticiler.f)):
            yy = r.y + 28 + i * 16
            T.yaz(ekran, ad.split()[0], (x0, yy - 2), 12, T.SOLUK, kalin=True)
            bx = x0 + 26
            orta = bx + cg // 2
            pygame.draw.rect(ekran, (12, 20, 31), (bx, yy + 1, cg, 9), border_radius=4)
            sinir = A.ITICI_ILERI_MAX if f >= 0 else A.ITICI_GERI_MAX
            uz = int((cg // 2) * max(-1.0, min(1.0, f / sinir)))
            renk = T.ILERI if f >= 0 else T.GERI
            if uz > 0:
                pygame.draw.rect(ekran, renk, (orta, yy + 1, uz, 9), border_radius=3)
            elif uz < 0:
                pygame.draw.rect(ekran, renk, (orta + uz, yy + 1, -uz, 9), border_radius=3)
            pygame.draw.line(ekran, T.SOLUK, (orta, yy - 1), (orta, yy + 11))
            T.yaz(ekran, f"{f:+5.1f} N", (r.right - 12, yy - 2), 12, T.YAZI, mono=True, hiza="sag")

    # ------------------------------------------------------------ #
    def _batarya(self, ekran, r, batarya):
        T.kart(ekran, r, "BATARYA")
        d = batarya.doluluk
        renk = T.YESIL if d > 0.5 else (T.SARI if d > 0.2 else T.KIRMIZI)
        # pil simgesi
        pil = pygame.Rect(r.x + 12, r.y + 30, 92, 40)
        pygame.draw.rect(ekran, (12, 20, 31), pil, border_radius=6)
        pygame.draw.rect(ekran, renk, (pil.x + 4, pil.y + 4, int((pil.w - 8) * d), pil.h - 8), border_radius=4)
        pygame.draw.rect(ekran, T.SOLUK, pil, 2, border_radius=6)
        pygame.draw.rect(ekran, T.SOLUK, (pil.right, pil.centery - 7, 5, 14), border_radius=2)
        T.yaz(ekran, f"%{d * 100:.1f}", (pil.centerx, pil.y + 9), 16, T.YAZI, kalin=True, hiza="orta")
        # değerler
        x0 = r.x + 126
        dk = batarya.kalan_dakika()
        kalan = "--" if dk == float("inf") else (f"{dk / 60:.1f} sa" if dk > 120 else f"{dk:.0f} dk")
        satirlar = [("Voltaj", f"{batarya.voltaj:5.2f} V"), ("Akım", f"{batarya.akim:5.1f} A"),
                    ("Güç", f"{batarya.guc:5.0f} W"), ("Kalan süre", kalan)]
        for i, (ad, deger) in enumerate(satirlar):
            sx = x0 + (i % 2) * 120
            sy = r.y + 26 + (i // 2) * 30
            T.yaz(ekran, ad, (sx, sy), 11, T.SOLUK)
            T.yaz(ekran, deger, (sx, sy + 13), 14, T.YAZI, kalin=True, mono=True)
        # anlık güç çubuğu (0–1500 W)
        g = r.w - 24
        oran = min(1.0, batarya.guc / 1500.0)
        pygame.draw.rect(ekran, (12, 20, 31), (r.x + 12, r.bottom - 13, g, 6), border_radius=3)
        pygame.draw.rect(ekran, T.TURUNCU, (r.x + 12, r.bottom - 13, int(g * oran), 6), border_radius=3)
