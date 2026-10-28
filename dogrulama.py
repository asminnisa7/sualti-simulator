"""
Doğrulama senaryoları: simülatörü ekran açmadan çalıştırır ve model dokümanındaki
(docs/MODEL.md) grafikleri docs/img/ klasörüne üretir.

Çalıştırma:  python dogrulama.py
"""
import math
import os
import random

import numpy as np
import matplotlib
matplotlib.use("Agg")                      # pencere açmadan dosyaya çiz
import matplotlib.pyplot as plt

import ayarlar as A
from fizik import rk4_adim
from itici import Iticiler
from kontrol import Otopilot
from sensorler import Sensorler
from kestirim import Kestirici
from batarya import motor_gucu

KLASOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "img")
os.makedirs(KLASOR, exist_ok=True)


def baslangic(z=2.0):
    return np.array([25.0, 12.5, z, 0.0, 0.0, 0.0, 0.0, 0.0])


def son_hiz(F, k):
    return (-k[0] + math.sqrt(k[0] ** 2 + 4 * k[1] * F)) / (2 * k[1])


def kaydet(fig, ad):
    fig.tight_layout()
    fig.savefig(os.path.join(KLASOR, ad), dpi=120)
    plt.close(fig)
    print(f"  docs/img/{ad}")


# 1) İleri basamak yanıtı ve analitik son hız
def ileri_basamak():
    fig, ax = plt.subplots(figsize=(7, 4))
    eski = A.KALDIRMA
    A.KALDIRMA = A.AGIRLIK
    for F in (20, 40, 80):
        d, t, u = baslangic(), [], []
        for i in range(1200):
            d = rk4_adim(d, np.array([F, 0, 0, 0.0]), (0, 0), A.DT)
            t.append((i + 1) * A.DT)
            u.append(d[4])
        cizgi, = ax.plot(t, u, label=f"F = {F} N")
        ax.axhline(son_hiz(F, A.K_ILERI), ls="--", lw=0.8, color=cizgi.get_color())
    A.KALDIRMA = eski
    ax.set_xlabel("zaman [s]")
    ax.set_ylabel("ileri hız u [m/s]")
    ax.set_title("İleri basamak yanıtı (kesikli çizgi: analitik son hız)")
    ax.grid(alpha=0.3)
    ax.legend()
    kaydet(fig, "ileri_basamak.png")


# 2) Dönüş çemberi: savrulma ve akıntının etkisi
def donus_cemberi():
    fig, ax = plt.subplots(figsize=(9, 4))
    eski = A.KALDIRMA
    A.KALDIRMA = A.AGIRLIK
    for akinti, etiket in (((0.0, 0.0), "akıntı yok"), ((0.25, 0.0), "0.25 m/s akıntı (+x yönünde)")):
        it, d, xs, ys = Iticiler(), baslangic(), [], []
        for _ in range(4000):
            it.dagit([40.0, 0, 0, 3.0])
            it.adim(A.DT)
            d = rk4_adim(d, it.toplam_kuvvet(), akinti, A.DT)
            xs.append(d[0])
            ys.append(d[1])
        ax.plot(xs, ys, label=etiket)
    A.KALDIRMA = eski
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("Dönüş çemberi (40 N ileri + 3 N·m dönüş, 40 s)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    kaydet(fig, "donus_cemberi.png")


# 3) Gürültülü sensörlerle otopilot basamak yanıtı
def otopilot_basamak():
    random.seed(1)
    d = baslangic()
    it, op, se, ke = Iticiler(), Otopilot(), Sensorler(), Kestirici(d)
    op.derinlik_degistir(d)
    op.bas_degistir(d)
    op.hedef_derinlik, op.hedef_bas = 4.0, math.radians(120)
    t, z, zt, zo, to, bas = [], [], [], [], [], []
    for i in range(3000):
        olc = se.olc(d, A.DT)
        ke.guncelle(olc, it.toplam_kuvvet(), A.DT)
        it.dagit(op.uygula(np.zeros(4), np.zeros(4), ke.durum(), A.DT))
        it.adim(A.DT)
        d = rk4_adim(d, it.toplam_kuvvet(), (0.15, 0.15), A.DT)
        t.append((i + 1) * A.DT)
        z.append(d[2])
        zt.append(ke.durum()[2])
        bas.append(math.degrees(d[3]))
        if olc["derinlik"] is not None:
            to.append((i + 1) * A.DT)
            zo.append(olc["derinlik"])
    fig, ax = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    ax[0].plot(to, zo, ".", ms=2, color="lightgray", label="ölçüm")
    ax[0].plot(t, zt, "r-", lw=1, label="Kalman tahmini")
    ax[0].plot(t, z, "b-", lw=1.5, label="gerçek")
    ax[0].axhline(4.0, ls="--", color="k", lw=0.8, label="hedef")
    ax[0].invert_yaxis()
    ax[0].set_ylabel("derinlik [m]")
    ax[0].set_title("Otopilot: 2 m → 4 m, 0° → 120° (gürültülü sensörler, akıntı var)")
    ax[0].legend(fontsize=8)
    ax[1].plot(t, bas)
    ax[1].axhline(120, ls="--", color="k", lw=0.8)
    ax[1].set_ylabel("baş açısı [°]")
    ax[1].set_xlabel("zaman [s]")
    for a in ax:
        a.grid(alpha=0.3)
    kaydet(fig, "otopilot_basamak.png")
    zs = np.array(z)
    return max(zs) - 4.0, abs(zs[-1] - 4.0)


# 4) Ölü hesap kayması
def olu_hesap():
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for tohum in range(1, 6):
        random.seed(tohum)
        d = baslangic()
        d[0], d[1] = 3.0, 12.5
        it, se, ke = Iticiler(), Sensorler(), Kestirici(d)
        op = Otopilot()
        op.derinlik_degistir(d)
        t, h = [], []
        for i in range(6000):
            olc = se.olc(d, A.DT)
            ke.guncelle(olc, it.toplam_kuvvet(), A.DT)
            pilot = np.array([1.0, 0, 0, 0.6 * math.sin(i * A.DT / 4)])
            it.dagit(op.uygula(pilot * np.array(A.ISTENEN_MAX) * 0.3, pilot, ke.durum(), A.DT))
            it.adim(A.DT)
            d = rk4_adim(d, it.toplam_kuvvet(), (0, 0), A.DT)
            t.append((i + 1) * A.DT)
            h.append(math.hypot(ke.x - d[0], ke.y - d[1]))
        ax.plot(t, h, lw=1)
    ax.set_xlabel("zaman [s]")
    ax.set_ylabel("konum hatası [m]")
    ax.set_title("Ölü hesap ile konum tahmini hatası (5 farklı rastgele deneme)")
    ax.grid(alpha=0.3)
    kaydet(fig, "olu_hesap.png")


# 5) Motor gücü - itki eğrisi
def guc_egrisi():
    F = np.linspace(0, 50, 100)
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.plot(F, [motor_gucu(f) for f in F])
    ax.set_xlabel("itki [N]")
    ax.set_ylabel("elektrik gücü [W]")
    ax.set_title("Tek motorun güç tüketimi (P ∝ F^1.5)")
    ax.grid(alpha=0.3)
    kaydet(fig, "guc_egrisi.png")


if __name__ == "__main__":
    print("Grafikler üretiliyor:")
    ileri_basamak()
    donus_cemberi()
    asma, son_hata = otopilot_basamak()
    olu_hesap()
    guc_egrisi()
    print(f"\nOtopilot derinlik aşması: {asma * 100:.1f} cm, son hata: {son_hata * 100:.1f} cm")
