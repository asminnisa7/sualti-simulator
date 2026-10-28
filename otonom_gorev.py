"""
Otonom görev: araç, insan pilot olmadan 5 kapıdan sırayla geçer.

Yöntem (rota noktası takibi):
  - Her kapı için kapının önünde ve arkasında birer rota noktası vardır; araç önce kapının
    önüne gelir, sonra kapının içinden geçerek arkasındaki noktaya gider. Bazı ara noktalar
    engellerin (sütunların) etrafından dolaşmak için eklenmiştir.
  - Yön: otopilotun baş sabitleme hedefi, aracın tahmini konumundan sıradaki noktaya olan
    yön açısına ayarlanır (bakış hattı / "line of sight" yönlendirmesi).
  - Derinlik: otopilotun derinlik hedefi, sıradaki kapının derinlik aralığının ortasıdır.
  - Hız: araç hedef yöne dönükse ileri gider, değilse yavaşlayıp önce döner.
  - Kurtarma: konum tahmini zamanla kaydığı için araç bir kapıyı kaçırabilir. Kapının son
    rota noktasına varıldığı halde kapı geçilmemişse araç geri dönüp kapıya yeniden yaklaşır.
  - Araç gerçek konumunu bilmez; sensörlerden kestirdiği konumu kullanır (ölü hesap).
    Kamera sıradaki kapıyı görünce konum tahmini kapının bilinen yerine göre düzeltilir.

Çalıştırma:  python otonom_gorev.py
Sonuç uçuş kaydı olarak kaydedilir; grafikleri:  python grafik.py
"""
import math

import numpy as np

import ayarlar as A
from fizik import rk4_adim
from itici import Iticiler
from ortam import Gorev, carpismalari_uygula
from kontrol import Otopilot, aci_farki
from akinti import Akinti
from batarya import Batarya
from sensorler import Sensorler
from kestirim import Kestirici
from kayit import UcusKaydi

# (rota noktası (x, y), hangi kapı için)
ROTA = [
    ((7.5, 12.5), 0), ((12.0, 12.5), 0),          # 1. kapı
    ((15.0, 19.0), 1), ((20.5, 19.0), 1),         # 2. kapı
    ((21.6, 14.2), 2),                            # sütunun yanından geç
    ((25.0, 7.0), 2), ((30.5, 7.0), 2),           # 3. kapı
    ((40.0, 9.5), 3), ((40.0, 15.0), 3),          # 4. kapı
    ((38.5, 20.8), 4),                            # sütunun etrafından dolaş
    ((33.0, 21.0), 4), ((27.5, 21.0), 4),         # 5. kapı
]
VARIS_YARICAPI = 0.7        # m: rota noktasına bu kadar yaklaşınca sıradakine geç
ILERI_GUC = 0.55            # hedefe dönükken ileri itki oranı


class OtonomPilot:
    def __init__(self, rota=ROTA):
        self.rota = rota
        self.kapi_no = 0          # hedeflenen kapı
        self.sira = 0             # o kapının rota noktalarından hangisinde olduğumuz
        self.yeniden_deneme = 0

    def komut(self, tahmin, gorev, otopilot):
        """Tahmini durumdan pilot komutunu üretir ve otopilot hedeflerini ayarlar."""
        if gorev.bitti:
            return np.zeros(4)
        if gorev.siradaki != self.kapi_no:            # kapı geçildi: sıradaki kapının rotasına başla
            self.kapi_no, self.sira = gorev.siradaki, 0
        noktalar = [p for p, k in self.rota if k == self.kapi_no]
        hx, hy = noktalar[self.sira]
        if math.hypot(hx - tahmin[0], hy - tahmin[1]) < VARIS_YARICAPI:
            if self.sira < len(noktalar) - 1:
                self.sira += 1
            else:                                     # son noktaya gelindi ama kapı geçilmedi: tekrar dene
                self.sira = 0
                self.yeniden_deneme += 1
            hx, hy = noktalar[self.sira]
        kapi = gorev.kapilar[self.kapi_no]
        otopilot.hedef_derinlik = (kapi.sig + kapi.derin) / 2
        yon = math.atan2(hy - tahmin[1], hx - tahmin[0])
        otopilot.hedef_bas = yon
        hata = abs(aci_farki(yon - tahmin[3]))
        ileri = ILERI_GUC if hata < math.radians(25) else 0.15
        return np.array([ileri, 0.0, 0.0, 0.0])


def gorevi_calistir(akinti_acik=False, en_uzun=180.0, kayit=None):
    x, y, z = A.BASLANGIC
    durum = np.array([x, y, z, 0.0, 0.0, 0.0, 0.0, 0.0])
    iticiler, gorev, otopilot = Iticiler(), Gorev(), Otopilot()
    akinti, batarya, sensorler = Akinti(), Batarya(), Sensorler()
    akinti.acik = akinti_acik
    kestirici = Kestirici(durum)
    pilot = OtonomPilot()
    otopilot.derinlik_degistir(durum)
    otopilot.bas_degistir(durum)

    zaman = 0.0
    while zaman < en_uzun and not gorev.bitti:
        akinti.adim(A.DT)
        ak = akinti.hiz_vektoru(durum[2])
        olcumler = sensorler.olc(durum, A.DT)
        kestirici.guncelle(olcumler, iticiler.toplam_kuvvet(), A.DT)
        kestirici.kapi_ile_duzelt(sensorler.kapi_olc(durum, gorev, A.DT), gorev.kapilar, A.DT)

        komut = pilot.komut(kestirici.durum(), gorev, otopilot)
        istenen = komut * np.array(A.ISTENEN_MAX)
        iticiler.guc_carpani = batarya.itki_carpani()
        # otopilot yön ve derinliği tutar (pilot dönme/dalma tuşuna basmıyor)
        iticiler.dagit(otopilot.uygula(istenen, np.zeros(4), kestirici.durum(), A.DT))
        iticiler.adim(A.DT)
        batarya.adim(iticiler.f, A.DT)

        durum = rk4_adim(durum, iticiler.toplam_kuvvet(), ak, A.DT)
        gorev.guncelle(durum, carpismalari_uygula(durum), A.DT)
        if kayit is not None:
            kayit.adim(zaman, A.DT, durum, kestirici, iticiler, batarya, ak, otopilot, gorev)
        zaman += A.DT
    gorev.yeniden_deneme = pilot.yeniden_deneme
    return gorev


if __name__ == "__main__":
    kayit = UcusKaydi()
    gorev = gorevi_calistir(kayit=kayit)
    if gorev.bitti:
        print(f"Görev tamamlandı: {gorev.siradaki} kapı, süre {gorev.sure:.1f} s, "
              f"çarpışma {gorev.carpisma_sayisi}")
    else:
        print(f"Görev tamamlanamadı: {gorev.siradaki} / {len(gorev.kapilar)} kapı geçildi")
    yol = kayit.kaydet()
    print(f"Uçuş kaydı: {yol}")
    print("Grafikler için:  python grafik.py")
