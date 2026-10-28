"""
Su Altı Aracı Simülatörü — ana program.
Klavye girişini okur, fiziği ilerletir ve çizimi yaptırır.
"""
import numpy as np
import pygame

import ayarlar as A
from fizik import rk4_adim
from itici import Iticiler
from ortam import Gorev, carpismalari_uygula
from arayuz import Cizici
from kontrol import Otopilot
from akinti import Akinti
from batarya import Batarya
from sensorler import Sensorler
from kestirim import Kestirici
from kayit import UcusKaydi


def baslangic_durumu():
    x, y, z = A.BASLANGIC
    return np.array([x, y, z, 0.0, 0.0, 0.0, 0.0, 0.0])   # [x, y, z, psi, u, v, w, r]


cizici = Cizici()
saat = pygame.time.Clock()
iticiler = Iticiler()
gorev = Gorev()
otopilot = Otopilot()
akinti = Akinti()
batarya = Batarya()
durum = baslangic_durumu()
sensorler = Sensorler()
kestirici = Kestirici(durum)
kayit = UcusKaydi()

guc = 0.5
birikim = 0.0
zaman = 0.0                  # simülasyon zamanı (s)

calisiyor = True
while calisiyor:
    kare_suresi = min(saat.tick(60) / 1000.0, 0.1)

    # --- Tek seferlik tuşlar ---
    for olay in pygame.event.get():
        if olay.type == pygame.QUIT:
            calisiyor = False
        elif olay.type == pygame.MOUSEWHEEL:
            cizici.yakinlastir(1.1 if olay.y > 0 else 1 / 1.1)
        elif olay.type == pygame.KEYDOWN:
            if cizici.yardim_goster and olay.key != pygame.K_ESCAPE:
                cizici.yardim_goster = False        # yardım açıkken herhangi bir tuş kapatır
            elif olay.key == pygame.K_ESCAPE:
                calisiyor = False
            elif olay.key in (pygame.K_TAB, pygame.K_F1):
                cizici.yardim_goster = True
            elif olay.key == pygame.K_v:
                cizici.gorunum_degistir()
            elif olay.key == pygame.K_h:
                otopilot.bas_degistir(kestirici.durum())
            elif olay.key == pygame.K_j:
                otopilot.derinlik_degistir(kestirici.durum())
            elif olay.key == pygame.K_l:
                yol = kayit.kaydet()
                gorev.mesaj = f"Kaydedildi: {yol}" if yol else "Kaydedilecek veri yok"
                gorev.mesaj_suresi = 3.0
            elif olay.key == pygame.K_n:
                sensorler.ideal = not sensorler.ideal
            elif olay.key == pygame.K_c:
                akinti.acik = not akinti.acik
            elif olay.key == pygame.K_t:
                akinti.turbulans = not akinti.turbulans
            elif olay.key == pygame.K_LEFT:
                akinti.yon -= 15
            elif olay.key == pygame.K_RIGHT:
                akinti.yon += 15
            elif olay.key == pygame.K_UP:
                akinti.hiz = min(1.5, akinti.hiz + 0.1)
            elif olay.key == pygame.K_DOWN:
                akinti.hiz = max(0.0, akinti.hiz - 0.1)
            elif olay.key == pygame.K_1:
                guc = 0.25
            elif olay.key == pygame.K_2:
                guc = 0.5
            elif olay.key == pygame.K_3:
                guc = 1.0
            elif olay.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                cizici.yakinlastir(1.2)
            elif olay.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                cizici.yakinlastir(1 / 1.2)
            elif olay.key == pygame.K_BACKSPACE:
                durum = baslangic_durumu()
                iticiler = Iticiler()
                gorev.sifirla()
                otopilot.kapat()
                batarya.sifirla()
                kestirici.sifirla(durum)
                kayit.sifirla()
                zaman = 0.0
                cizici.izi_sifirla()

    # --- Basılı tuşlar -> pilotun istediği kuvvetler ---
    tuslar = pygame.key.get_pressed()
    pilot = np.array([
        tuslar[pygame.K_w] - tuslar[pygame.K_s],
        tuslar[pygame.K_e] - tuslar[pygame.K_q],
        tuslar[pygame.K_f] - tuslar[pygame.K_r],
        tuslar[pygame.K_d] - tuslar[pygame.K_a],
    ], dtype=float)
    istenen = pilot * np.array(A.ISTENEN_MAX) * guc

    # --- Sabit adımlı fizik (100 Hz) ---
    birikim += kare_suresi
    while birikim >= A.DT:
        akinti.adim(A.DT)
        ak = akinti.hiz_vektoru(durum[2])            # aracın bulunduğu derinlikteki akıntı

        # Araç yazılımı gerçek durumu göremez: sensörlerle ölçer ve tahmin eder
        olcumler = sensorler.olc(durum, A.DT)
        kestirici.guncelle(olcumler, iticiler.toplam_kuvvet(), A.DT)
        kestirici.kapi_ile_duzelt(sensorler.kapi_olc(durum, gorev, A.DT), gorev.kapilar, A.DT)

        iticiler.guc_carpani = batarya.itki_carpani()
        iticiler.dagit(otopilot.uygula(istenen, pilot, kestirici.durum(), A.DT))
        iticiler.adim(A.DT)
        batarya.adim(iticiler.f, A.DT)

        durum = rk4_adim(durum, iticiler.toplam_kuvvet(), ak, A.DT)
        carpti = carpismalari_uygula(durum)
        gorev.guncelle(durum, carpti, A.DT)
        kayit.adim(zaman, A.DT, durum, kestirici, iticiler, batarya, ak, otopilot, gorev)
        zaman += A.DT
        birikim -= A.DT

    cizici.ciz(durum, iticiler, gorev, akinti.hiz_vektoru(durum[2]), akinti.acik, guc,
               kare_suresi, otopilot, batarya, akinti.turbulans, kestirici, sensorler)

# Kapanışta kaydı otomatik yaz
yol = kayit.kaydet()
if yol:
    print(f"Uçuş kaydı yazıldı: {yol}")
    print("Grafikleri görmek için:  python grafik.py")
pygame.quit()
