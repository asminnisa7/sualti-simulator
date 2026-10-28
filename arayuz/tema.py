"""
Arayüzün renk teması ve ortak çizim yardımcıları (yazı, kart, rozet, ok).
"""
import math

import pygame

# --- Renkler ---
ARKA = (10, 15, 24)
KART = (19, 28, 41)
KART_KENAR = (40, 55, 76)
YAZI = (226, 234, 242)
SOLUK = (124, 142, 165)
SONUK = (70, 84, 104)
VURGU = (86, 182, 255)
YESIL = (72, 214, 120)
SARI = (250, 204, 72)
TURUNCU = (255, 150, 70)
KIRMIZI = (240, 84, 84)
ARAC = (245, 196, 52)
ILERI = (255, 128, 80)      # motor ileri itiyor
GERI = (100, 170, 255)      # motor geri itiyor
HAYALET = (200, 230, 255)

_fontlar = {}


def font(boyut, kalin=False, mono=False):
    """Yazı tipini bir kez oluşturup saklar (her karede yeniden oluşturmak yavaştır)."""
    anahtar = (boyut, kalin, mono)
    if anahtar not in _fontlar:
        ad = "consolas,dejavusansmono,menlo,couriernew" if mono else "segoeui,dejavusans,arial"
        _fontlar[anahtar] = pygame.font.SysFont(ad, boyut, bold=kalin)
    return _fontlar[anahtar]


_yazi_onbellegi = {}


def yaz(ekran, metin, konum, boyut=15, renk=YAZI, kalin=False, mono=False, hiza="sol"):
    """Metni yazar ve genişliğini döndürür. hiza: 'sol', 'orta' ya da 'sag'.
    Aynı yazı her karede yeniden oluşturulmasın diye oluşturulan resimler saklanır."""
    anahtar = (metin, boyut, tuple(renk), kalin, mono)
    resim = _yazi_onbellegi.get(anahtar)
    if resim is None:
        if len(_yazi_onbellegi) > 1500:
            _yazi_onbellegi.clear()
        resim = font(boyut, kalin, mono).render(metin, True, renk)
        _yazi_onbellegi[anahtar] = resim
    x, y = konum
    if hiza == "orta":
        x -= resim.get_width() // 2
    elif hiza == "sag":
        x -= resim.get_width()
    ekran.blit(resim, (int(x), int(y)))
    return resim.get_width()


def metin_genisligi(metin, boyut=15, kalin=False, mono=False):
    return font(boyut, kalin, mono).size(metin)[0]


def kart(ekran, rect, baslik=None, sag_yazi=None):
    """Yuvarlatılmış köşeli panel kartı."""
    pygame.draw.rect(ekran, KART, rect, border_radius=10)
    pygame.draw.rect(ekran, KART_KENAR, rect, 1, border_radius=10)
    if baslik:
        yaz(ekran, baslik, (rect.x + 12, rect.y + 7), 12, SOLUK, kalin=True)
    if sag_yazi:
        yaz(ekran, sag_yazi, (rect.right - 12, rect.y + 7), 12, SOLUK, hiza="sag")


def yari_saydam(ekran, rect, renk, alfa, yaricap=8):
    """Yarı saydam yuvarlatılmış kutu."""
    yuzey = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(yuzey, (*renk, alfa), yuzey.get_rect(), border_radius=yaricap)
    ekran.blit(yuzey, (rect.x, rect.y))


def tus(ekran, x, y, metin, boyut=12):
    """Klavye tuşu görünümünde küçük kutu. Genişliğini döndürür."""
    g = max(20, metin_genisligi(metin, boyut, kalin=True) + 10)
    r = pygame.Rect(x, y, g, boyut + 8)
    pygame.draw.rect(ekran, (44, 58, 80), r, border_radius=4)
    pygame.draw.rect(ekran, (90, 108, 134), r, 1, border_radius=4)
    yaz(ekran, metin, (r.centerx, y + 3), boyut, YAZI, kalin=True, hiza="orta")
    return g


def rozet(ekran, x, y, metin, tus_adi, acik=True, renk=YESIL):
    """Üst çubuktaki mod rozeti: [tuş] METİN. Genişliğini döndürür."""
    boyut = 12
    g_tus = metin_genisligi(tus_adi, 11, kalin=True) + 8
    g = g_tus + metin_genisligi(metin, boyut, kalin=True) + 18
    r = pygame.Rect(x, y, g, 26)
    if acik:
        koyu = tuple(int(c * 0.25) for c in renk)
        pygame.draw.rect(ekran, koyu, r, border_radius=13)
        pygame.draw.rect(ekran, renk, r, 1, border_radius=13)
        yazi_rengi = renk
    else:
        pygame.draw.rect(ekran, KART, r, border_radius=13)
        pygame.draw.rect(ekran, KART_KENAR, r, 1, border_radius=13)
        yazi_rengi = SONUK
    kutu = pygame.Rect(x + 5, y + 5, g_tus, 16)
    pygame.draw.rect(ekran, (36, 48, 66), kutu, border_radius=4)
    yaz(ekran, tus_adi, (kutu.centerx, y + 5), 11, SOLUK, kalin=True, hiza="orta")
    yaz(ekran, metin, (x + g_tus + 11, y + 5), boyut, yazi_rengi, kalin=True)
    return g


def ok(ekran, a, b, renk, kalinlik=2, uc=9):
    """a'dan b'ye ok çizer."""
    a = (int(a[0]), int(a[1]))
    b = (int(b[0]), int(b[1]))
    pygame.draw.line(ekran, renk, a, b, kalinlik)
    aci = math.atan2(b[1] - a[1], b[0] - a[0])
    for d in (2.6, -2.6):
        q = (int(b[0] + uc * math.cos(aci + d)), int(b[1] + uc * math.sin(aci + d)))
        pygame.draw.line(ekran, renk, b, q, kalinlik)


def kesikli_cizgi(ekran, renk, a, b, parca=6, bosluk=5, kalinlik=1):
    uzunluk = math.hypot(b[0] - a[0], b[1] - a[1])
    if uzunluk < 1:
        return
    dx, dy = (b[0] - a[0]) / uzunluk, (b[1] - a[1]) / uzunluk
    s = 0.0
    while s < uzunluk:
        e = min(s + parca, uzunluk)
        pygame.draw.line(ekran, renk, (int(a[0] + dx * s), int(a[1] + dy * s)),
                         (int(a[0] + dx * e), int(a[1] + dy * e)), kalinlik)
        s += parca + bosluk
