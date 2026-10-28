"""
Arayüz paketi. Dışarıya tek bir sınıf verir: Cizici.

  tema.py   : renkler, yazı tipleri, ortak çizim yardımcıları
  sahne.py  : üstten havuz görünümü, yan kesit şeridi ve mini harita
  kamera3b.py: aracın arkasından bakan 3B takip kamerası
  arac_modeli.py: BlueROV2 Heavy benzeri 3B araç modeli (üç görünümde de kullanılır)
  efektler.py: motor kabarcıkları ve havuz tabanındaki ışık desenleri (kostikler)
  panel.py  : üst durum çubuğu ve sağdaki gösterge kartları
  yardim.py : F1 yardım penceresi
"""
import pygame

from .sahne import Sahne
from .panel import Panel, ust_cubuk
from .yardim import yardim_ciz
from .kamera3b import Kamera3B
from .arac_modeli import AracModeli
from .efektler import Kabarciklar, Kostik

GENISLIK, YUKSEKLIK = 1280, 720
UST_CUBUK = 44
PANEL_G = 380


class Cizici:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Su Altı Aracı Simülatörü")
        self.ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
        self.ust = pygame.Rect(0, 0, GENISLIK, UST_CUBUK)
        self.model = AracModeli()
        self.kabarciklar = Kabarciklar()
        self.sahne = Sahne(pygame.Rect(0, UST_CUBUK, GENISLIK - PANEL_G, YUKSEKLIK - UST_CUBUK),
                           self.model, self.kabarciklar, Kostik())
        self.panel = Panel(pygame.Rect(GENISLIK - PANEL_G, UST_CUBUK, PANEL_G, YUKSEKLIK - UST_CUBUK))
        self.kamera3b = Kamera3B(self.model, self.kabarciklar)
        self.gorunum = "ust"               # "ust": üstten görünüm, "3b": takip kamerası
        self.yardim_goster = True          # ilk açılışta kontroller görünsün

    def gorunum_degistir(self):
        self.gorunum = "3b" if self.gorunum == "ust" else "ust"

    def yakinlastir(self, carpan):
        self.sahne.yakinlastir(carpan)

    def izi_sifirla(self):
        self.sahne.izi_sifirla()
        self.panel.sifirla()
        self.kabarciklar.sifirla()

    def ciz(self, durum, iticiler, gorev, akinti, akinti_acik, guc, kare_suresi, otopilot,
            batarya, turbulans, kestirici, sensorler):
        self.sahne.iz_ekle(durum)
        self.model.pervaneleri_dondur(iticiler.f, kare_suresi)
        self.kabarciklar.guncelle(durum, iticiler.f, akinti, kare_suresi)
        if self.gorunum == "ust":
            self.sahne.ciz(self.ekran, durum, iticiler, gorev, akinti, otopilot, kestirici, kare_suresi)
        else:
            alan = self.sahne.rect
            self.kamera3b.ciz(self.ekran, alan, durum, iticiler, gorev, otopilot, kestirici,
                              self.sahne.iz, kare_suresi, akinti)
            self.ekran.set_clip(alan)
            self.sahne._mini_harita(self.ekran, durum, gorev, kestirici.durum(), alan, kamera_alani=False)
            self.sahne._gorunum_etiketi(self.ekran, "3B TAKİP KAMERASI", "üstten görünüm", alan)
            self.sahne.kamera_rozeti(self.ekran, kestirici, alan)
            self.sahne._mesaj(self.ekran, gorev, alan)
            self.ekran.set_clip(None)
        self.panel.ciz(self.ekran, durum, iticiler, gorev, akinti, akinti_acik, otopilot, batarya,
                       kestirici, kare_suresi)
        ust_cubuk(self.ekran, self.ust, otopilot, akinti, akinti_acik, turbulans, sensorler, guc)
        if self.yardim_goster:
            yardim_ciz(self.ekran)
        pygame.display.flip()
