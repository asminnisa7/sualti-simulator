"""
Uçuş kaydını grafikler.

Kullanım:  python grafik.py                       (en son kayıt)
           python grafik.py kayitlar/ucus_X.csv   (belirli bir kayıt)
Grafik ekranda açılır ve aynı adla .png olarak da kaydedilir.
"""
import csv
import glob
import math
import os
import sys

import matplotlib.pyplot as plt

import ayarlar as A
from ortam import Kapi


def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        satirlar = list(csv.DictReader(dosya))
    return {anahtar: [float(s[anahtar]) for s in satirlar] for anahtar in satirlar[0]}


def main():
    if len(sys.argv) > 1:
        yol = sys.argv[1]
    else:
        klasor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kayitlar")
        dosyalar = sorted(glob.glob(os.path.join(klasor, "*.csv")))
        if not dosyalar:
            sys.exit("kayitlar/ klasöründe kayıt yok. Önce simülatörü çalıştırıp kapatın.")
        yol = dosyalar[-1]
    d = oku(yol)
    t = d["zaman"]

    fig, eksen = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle(f"Uçuş kaydı: {os.path.basename(yol)}", fontsize=14)

    # 1) Üstten yörünge
    ax = eksen[0, 0]
    ax.add_patch(plt.Rectangle((0, 0), A.HAVUZ_UZUNLUK, A.HAVUZ_GENISLIK,
                               fill=True, color="#d6eaf8", zorder=0))
    for ex, ey, er in A.ENGELLER:
        ax.add_patch(plt.Circle((ex, ey), er, color="gray"))
    for i, k in enumerate(A.KAPILAR):
        kapi = Kapi(*k)
        (x1, y1), (x2, y2) = kapi.direkler()
        ax.plot([x1, x2], [y1, y2], "g-", lw=3)
        ax.text(x2 + 0.5, y2, str(i + 1), color="green")
    ax.plot(d["x"], d["y"], "b-", lw=1.5, label="gerçek")
    ax.plot(d["x_tahmin"], d["y_tahmin"], "r--", lw=1, label="tahmin (ölü hesap)")
    ax.set_xlim(0, A.HAVUZ_UZUNLUK)
    ax.set_ylim(A.HAVUZ_GENISLIK, 0)           # ekranla aynı yön: y aşağı doğru artar
    ax.set_aspect("equal")
    ax.set_title("Yörünge (üstten)")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.legend(loc="lower right", fontsize=8)

    # 2) Derinlik
    ax = eksen[0, 1]
    ax.plot(t, d["z_olcum"], ".", color="lightgray", ms=2, label="ölçüm")
    ax.plot(t, d["z_tahmin"], "r-", lw=1, label="Kalman tahmini")
    ax.plot(t, d["z"], "b-", lw=1.5, label="gerçek")
    hedef = [h if a else math.nan for h, a in zip(d["hedef_derinlik"], d["derinlik_sabitleme"])]
    ax.plot(t, hedef, "k--", lw=1, label="otopilot hedefi")
    ax.invert_yaxis()
    ax.set_title("Derinlik")
    ax.set_xlabel("zaman [s]")
    ax.set_ylabel("derinlik [m]")
    ax.legend(fontsize=8)

    # 3) Hızlar
    ax = eksen[0, 2]
    ax.plot(t, d["u"], label="u (ileri)")
    ax.plot(t, d["v"], label="v (yan)")
    ax.plot(t, d["w"], label="w (dikey)")
    ax.set_title("Hızlar (araç ekseninde)")
    ax.set_xlabel("zaman [s]")
    ax.set_ylabel("[m/s]")
    ax.legend(fontsize=8)

    # 4) Motor kuvvetleri
    ax = eksen[1, 0]
    for i, (ad, *_) in enumerate(A.ITICILER):
        ax.plot(t, d[f"f{i + 1}"], lw=0.8, label=ad)
    ax.set_title("Motor kuvvetleri")
    ax.set_xlabel("zaman [s]")
    ax.set_ylabel("[N]")
    ax.legend(fontsize=7, ncol=2)

    # 5) Batarya
    ax = eksen[1, 1]
    ax.plot(t, d["guc_W"], color="orange", lw=0.8)
    ax.set_ylabel("anlık güç [W]", color="orange")
    ax2 = ax.twinx()
    ax2.plot(t, d["batarya_yuzde"], color="green", lw=1.5)
    ax2.set_ylabel("batarya [%]", color="green")
    toplam_wh = sum(d["guc_W"]) * (t[1] - t[0]) / 3600 if len(t) > 1 else 0
    ax.set_title(f"Güç tüketimi (toplam {toplam_wh:.1f} Wh)")
    ax.set_xlabel("zaman [s]")

    # 6) Konum tahmini hatası
    ax = eksen[1, 2]
    hata = [math.hypot(a - b, c - e) for a, b, c, e in zip(d["x_tahmin"], d["x"], d["y_tahmin"], d["y"])]
    ax.plot(t, hata, "r-")
    ax.set_title("Konum tahmini hatası (ölü hesap kayması)")
    ax.set_xlabel("zaman [s]")
    ax.set_ylabel("[m]")

    for ax in eksen.flat:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    png = os.path.splitext(yol)[0] + ".png"
    fig.savefig(png, dpi=110)
    print(f"Grafik kaydedildi: {png}")
    plt.show()


if __name__ == "__main__":
    main()
