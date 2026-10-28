"""F1 ile açılan yardım penceresi."""
import pygame

from . import tema as T

GRUPLAR = [
    ("SÜRÜŞ", [("W / S", "ileri / geri"), ("Q / E", "sola / sağa yanal kayma"),
               ("A / D", "sola / sağa dönüş"), ("R / F", "yukarı çıkma / dalma"),
               ("1 2 3", "güç %25 / %50 / %100")]),
    ("OTOPİLOT", [("H", "yön sabitleme"), ("J", "derinlik sabitleme")]),
    ("ORTAM", [("C", "akıntı aç / kapa"), ("T", "türbülans aç / kapa"),
               ("← →", "akıntı yönü"), ("↑ ↓", "akıntı hızı"), ("N", "sensör: gerçekçi / ideal")]),
    ("DİĞER", [("+ / −", "yakınlaştır (fare tekerleği de olur)"), ("L", "uçuş kaydını kaydet"),
               ("⌫", "görevi baştan başlat (Backspace)"), ("V", "görünüm: üstten / 3B kamera"), ("TAB", "bu pencereyi aç"),
               ("ESC", "çıkış")]),
]


def yardim_ciz(ekran):
    w, h = ekran.get_width(), ekran.get_height()
    karartma = pygame.Surface((w, h), pygame.SRCALPHA)
    karartma.fill((0, 0, 0, 150))
    ekran.blit(karartma, (0, 0))

    r = pygame.Rect(0, 0, 700, 480)
    r.center = (w // 2, h // 2)
    T.kart(ekran, r)
    T.yaz(ekran, "KONTROLLER", (r.x + 24, r.y + 18), 22, T.YAZI, kalin=True)
    T.yaz(ekran, "Kapatmak için herhangi bir tuşa bas", (r.right - 24, r.y + 24), 13, T.SARI, hiza="sag")

    sutunlar = [GRUPLAR[:2], GRUPLAR[2:]]
    for s, gruplar in enumerate(sutunlar):
        x = r.x + 24 + s * 340
        y = r.y + 62
        for baslik, satirlar in gruplar:
            T.yaz(ekran, baslik, (x, y), 12, T.VURGU, kalin=True)
            y += 22
            for tus_adi, aciklama in satirlar:
                T.tus(ekran, x, y, tus_adi)
                T.yaz(ekran, aciklama, (x + 62, y + 2), 14, T.YAZI)
                y += 27
            y += 10

    T.yaz(ekran, "GÖREV", (r.x + 24, r.bottom - 54), 12, T.VURGU, kalin=True)
    T.yaz(ekran, "Kapıları sırayla, ok yönünde ve etiketinde yazan derinlik aralığında geç.",
          (r.x + 80, r.bottom - 55), 13, T.YAZI)
    T.yaz(ekran, "Sıradaki kapı yeşilse derinliğin doğru, turuncuysa yanlış.",
          (r.x + 80, r.bottom - 35), 13, T.SOLUK)
