"""
Simülatörün doğrulama testleri.

Çalıştırma:   python -m pytest -v        (pytest kuruluysa)
       veya:  python test_simulator.py

Her test, sonucu analitik olarak (elle hesaplanarak) bilinen ya da fiziksel olarak
mutlaka sağlanması gereken bir davranışı kontrol eder.
"""
import math
import random

import numpy as np

import ayarlar as A
from fizik import rk4_adim, M
from itici import Iticiler
from kontrol import Otopilot, aci_farki
from sensorler import Sensorler
from kestirim import Kestirici
from ortam import Gorev, carpismalari_uygula
from batarya import Batarya, motor_gucu
from akinti import Akinti


# ------------------------------------------------------------------ #
# Yardımcılar
# ------------------------------------------------------------------ #
class NotrYuzerlik:
    """Test süresince kaldırma kuvvetini ağırlığa eşitler (tek bir etkiyi izole etmek için)."""

    def __enter__(self):
        self.eski = A.KALDIRMA
        A.KALDIRMA = A.AGIRLIK

    def __exit__(self, *hata):
        A.KALDIRMA = self.eski


def calistir(durum, kuvvet, sure, akinti=(0.0, 0.0)):
    for _ in range(int(round(sure / A.DT))):
        durum = rk4_adim(durum, np.array(kuvvet, dtype=float), akinti, A.DT)
    return durum


def baslangic(z=2.0, psi=0.0):
    return np.array([25.0, 12.5, z, psi, 0.0, 0.0, 0.0, 0.0])


def son_hiz(F, k):
    """F = k1*v + k2*v^2 denkleminin pozitif kökü."""
    return (-k[0] + math.sqrt(k[0] ** 2 + 4 * k[1] * F)) / (2 * k[1])


# ------------------------------------------------------------------ #
# Fizik
# ------------------------------------------------------------------ #
def test_kuvvet_yoksa_arac_kimildamaz():
    with NotrYuzerlik():
        d = calistir(baslangic(), [0, 0, 0, 0], 10)
    assert np.allclose(d, baslangic(), atol=1e-9)


def test_ileri_son_hiz_analitik_cozumle_ayni():
    with NotrYuzerlik():
        d = calistir(baslangic(), [40, 0, 0, 0], 20)
    assert abs(d[4] - son_hiz(40, A.K_ILERI)) < 1e-3     # 1.38 m/s
    assert abs(d[5]) < 1e-9 and abs(d[7]) < 1e-9          # yana kayma ve dönüş yok


def test_dikey_son_hiz_analitik_cozumle_ayni():
    eski = A.MAX_DERINLIK
    A.MAX_DERINLIK = 1000.0                               # dibe çarpmasın
    try:
        with NotrYuzerlik():
            d = calistir(baslangic(), [0, 0, 40, 0], 20)
    finally:
        A.MAX_DERINLIK = eski
    assert abs(d[6] - son_hiz(40, A.K_DIKEY)) < 1e-3


def test_eklenmis_kutle_hizlanmayi_yavaslatir():
    """Aynı kuvvetle yana hızlanma, ileriye göre daha yavaş olmalı (yan etkin kütle daha büyük)."""
    with NotrYuzerlik():
        ileri = calistir(baslangic(), [20, 0, 0, 0], 0.2)[4]
        yan = calistir(baslangic(), [0, 20, 0, 0], 0.2)[5]
    assert yan < ileri
    assert abs(ileri / yan - M[1] / M[0]) < 0.05          # ilk anda oran kütle oranına eşit


def test_enerji_kendiliginden_artmaz():
    """Dış kuvvet yokken kinetik enerji sürtünme yüzünden sadece azalabilir."""
    with NotrYuzerlik():
        d = baslangic()
        d[4:8] = [1.0, 0.5, 0.3, 1.0]
        onceki = 0.5 * np.sum(M * d[4:8] ** 2)
        for _ in range(500):
            d = rk4_adim(d, np.zeros(4), (0.0, 0.0), A.DT)
            enerji = 0.5 * np.sum(M * d[4:8] ** 2)
            assert enerji <= onceki + 1e-9
            onceki = enerji


def test_akintiya_kapilan_arac_akinti_hizina_ulasir():
    with NotrYuzerlik():
        d = calistir(baslangic(), [0, 0, 0, 0], 60, akinti=(0.0, 0.4))
    c, s = math.cos(d[3]), math.sin(d[3])
    vy = s * d[4] + c * d[5]                              # dünya eksenindeki y hızı
    assert abs(vy - 0.4) < 1e-3


def test_pozitif_yuzer_arac_yuzeye_cikar_ve_gecmez():
    d = calistir(baslangic(z=3.0), [0, 0, 0, 0], 60)      # B > W
    assert d[2] == 0.0


def test_rk4_dorduncu_derece_yakinsar():
    """Adım yarıya inince hata ~16 kat azalmalı (4. derece yöntemin imzası)."""
    with NotrYuzerlik():
        kuvvet, akinti = [40, 10, 0, 2], (0.2, 0.3)

        def entegre(dt):
            d = baslangic()
            for _ in range(int(round(2.0 / dt))):
                d = rk4_adim(d, np.array(kuvvet, dtype=float), akinti, dt)
            return d

        referans = entegre(0.0005)
        h1 = np.linalg.norm(entegre(0.04) - referans)
        h2 = np.linalg.norm(entegre(0.02) - referans)
    assert h1 / h2 > 10


# ------------------------------------------------------------------ #
# Motorlar
# ------------------------------------------------------------------ #
def test_saf_ileri_komut_yan_etki_uretmez():
    it = Iticiler()
    it.dagit([40, 0, 0, 0])
    it.f = it.komut
    assert np.allclose(it.toplam_kuvvet(), [40, 0, 0, 0], atol=1e-9)


def test_doyum_sinirlari_asmaz_ve_yonu_korur():
    it = Iticiler()
    istenen = np.array([500.0, 0, 0, 50.0])               # imkânsız büyük komut
    it.dagit(istenen)
    it.f = it.komut
    for f in it.komut:
        assert (f <= A.ITICI_ILERI_MAX + 1e-9) and (f >= -A.ITICI_GERI_MAX - 1e-9)
    tau = it.toplam_kuvvet()
    assert abs(tau[0] / tau[3] - istenen[0] / istenen[3]) < 1e-6


def test_motor_gecikmesi_zaman_sabitinde_yuzde_63():
    it = Iticiler()
    it.dagit([40, 0, 0, 0])
    for _ in range(int(round(A.ITICI_ZAMAN_SABITI / A.DT))):
        it.adim(A.DT)
    oran = it.f[0] / it.komut[0]
    assert abs(oran - (1 - math.exp(-1))) < 0.01          # birinci derece sistem: %63.2


# ------------------------------------------------------------------ #
# Otopilot, sensörler ve kestirim
# ------------------------------------------------------------------ #
def kapali_cevrim(sure, hedef_z, hedef_bas, akinti=(0.0, 0.0), ideal=False, tohum=1):
    random.seed(tohum)
    d = baslangic()
    it, op, se, ke = Iticiler(), Otopilot(), Sensorler(), Kestirici(d)
    se.ideal = ideal
    op.derinlik_degistir(d)
    op.bas_degistir(d)
    op.hedef_derinlik, op.hedef_bas = hedef_z, hedef_bas
    olcum_hatasi, tahmin_hatasi = [], []
    for i in range(int(round(sure / A.DT))):
        olcumler = se.olc(d, A.DT)
        ke.guncelle(olcumler, it.toplam_kuvvet(), A.DT)
        it.dagit(op.uygula(np.zeros(4), np.zeros(4), ke.durum(), A.DT))
        it.adim(A.DT)
        d = rk4_adim(d, it.toplam_kuvvet(), akinti, A.DT)
        if olcumler["derinlik"] is not None and i * A.DT > 5:
            olcum_hatasi.append(olcumler["derinlik"] - d[2])
            tahmin_hatasi.append(ke.durum()[2] - d[2])
    return d, ke, olcum_hatasi, tahmin_hatasi


def test_otopilot_derinlige_ve_yone_oturur():
    d, *_ = kapali_cevrim(25, hedef_z=4.0, hedef_bas=math.radians(120),
                          akinti=(0.2, 0.2), ideal=True)
    assert abs(d[2] - 4.0) < 0.02
    assert abs(math.degrees(aci_farki(d[3] - math.radians(120)))) < 1.0


def test_gurultulu_sensorlerle_otopilot_calisir():
    d, *_ = kapali_cevrim(30, hedef_z=3.0, hedef_bas=math.radians(45))
    assert abs(d[2] - 3.0) < 0.06
    assert abs(math.degrees(aci_farki(d[3] - math.radians(45)))) < 2.0


def test_kalman_filtresi_gurultuyu_azaltir():
    _, _, olcum, tahmin = kapali_cevrim(40, hedef_z=3.0, hedef_bas=0.0)
    assert np.std(tahmin) < 0.7 * np.std(olcum)


def test_jiroskop_kaymasi_ogrenilir():
    _, ke, *_ = kapali_cevrim(60, hedef_z=2.0, hedef_bas=0.0)
    assert abs(ke.kayma - A.JIROSKOP_KAYMA) < 0.002


# ------------------------------------------------------------------ #
# Görev ortamı
# ------------------------------------------------------------------ #
def kapiya_dogru_git(z):
    """Aracı 1. kapının 2 m önünden, verilen derinlikte kapıya doğru sür."""
    g = Gorev()
    k = g.kapilar[0]
    d = np.array([k.x - 2.0, k.y, z, 0.0, 0.0, 0.0, 0.0, 0.0])
    with NotrYuzerlik():
        for _ in range(400):
            d = rk4_adim(d, np.array([40.0, 0, 0, 0]), (0.0, 0.0), A.DT)
            g.guncelle(d, carpismalari_uygula(d), A.DT)
    return g


def test_kapi_dogru_derinlikte_gecilir():
    k = Gorev().kapilar[0]
    assert kapiya_dogru_git((k.sig + k.derin) / 2).siradaki == 1


def test_kapi_yanlis_derinlikte_sayilmaz():
    k = Gorev().kapilar[0]
    assert kapiya_dogru_git(k.derin + 1.0).siradaki == 0


def test_arac_duvardan_ve_sutundan_gecemez():
    d = np.array([1.0, 12.5, 1.0, math.pi, 0.0, 0.0, 0.0, 0.0])   # duvara doğru bakıyor
    with NotrYuzerlik():
        for _ in range(500):
            d = rk4_adim(d, np.array([40.0, 0, 0, 0]), (0.0, 0.0), A.DT)
            carpismalari_uygula(d)
    assert d[0] >= A.ARAC_YARICAP - 1e-9

    ex, ey, er = A.ENGELLER[0]
    d = np.array([ex - 2.0, ey, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])    # sütuna doğru
    with NotrYuzerlik():
        for _ in range(500):
            d = rk4_adim(d, np.array([40.0, 0, 0, 0]), (0.0, 0.0), A.DT)
            carpismalari_uygula(d)
            assert math.hypot(d[0] - ex, d[1] - ey) >= er + A.ARAC_YARICAP - 1e-6


# ------------------------------------------------------------------ #
# Batarya ve akıntı
# ------------------------------------------------------------------ #
def test_motor_gucu_itkinin_1_5_kuvvetiyle_artar():
    assert abs(motor_gucu(40) / motor_gucu(20) - 2 ** 1.5) < 1e-9
    assert 300 < motor_gucu(50) < 400                     # T200'ün tam güç tüketimine yakın


def test_batarya_bitince_motorlar_durur():
    b = Batarya()
    b.kalan_wh = 0.0
    it = Iticiler()
    it.guc_carpani = b.itki_carpani()
    it.dagit([40, 0, 0, 0])
    assert np.all(it.komut == 0)


def test_turbulansli_akintinin_ortalamasi_korunur():
    random.seed(3)
    ak = Akinti()
    ak.acik, ak.hiz, ak.yon = True, 0.5, 0.0
    ornekler = []
    for _ in range(30000):
        ak.adim(A.DT)
        ornekler.append(ak.hiz_vektoru(0.0)[0])
    assert abs(np.mean(ornekler) - 0.5) < 0.05
    assert np.std(ornekler) > 0.05                        # gerçekten dalgalanıyor
    assert ak.hiz_vektoru(A.MAX_DERINLIK)[0] < ak.hiz_vektoru(0.0)[0]   # dipte daha zayıf


# ------------------------------------------------------------------ #
# Otonom görev
# ------------------------------------------------------------------ #
def test_kapi_kamerasi_konum_hatasini_duzeltir():
    """Konum tahmini 1 m kaymışken kapıya bakan araç, kamera ölçümleriyle hatayı küçültmeli."""
    random.seed(2)
    g = Gorev()
    k = g.kapilar[0]
    d = np.array([k.x - 4.0, k.y, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0])
    ke, se = Kestirici(d), Sensorler()
    ke.x, ke.y = d[0] + 0.7, d[1] - 0.7                   # yanlış başlangıç tahmini (~1 m)
    for _ in range(500):                                   # 5 saniye, araç duruyor
        ke.kapi_ile_duzelt(se.kapi_olc(d, g, A.DT), g.kapilar, A.DT)
    assert math.hypot(ke.x - d[0], ke.y - d[1]) < 0.2


def test_otonom_gorev_tum_kapilari_carpismasiz_gecer():
    from otonom_gorev import gorevi_calistir
    random.seed(5)
    gorev = gorevi_calistir()
    assert gorev.bitti
    assert gorev.carpisma_sayisi == 0


def test_otonom_gorev_turbulansli_akintida_tamamlanir():
    from otonom_gorev import gorevi_calistir
    random.seed(2)
    gorev = gorevi_calistir(akinti_acik=True)
    assert gorev.bitti


# ------------------------------------------------------------------ #
if __name__ == "__main__":
    testler = [(ad, f) for ad, f in list(globals().items()) if ad.startswith("test_")]
    gecen = 0
    for ad, f in testler:
        try:
            f()
            print(f"GEÇTİ   {ad}")
            gecen += 1
        except AssertionError:
            print(f"KALDI   {ad}")
    print(f"\n{gecen} / {len(testler)} test geçti.")
