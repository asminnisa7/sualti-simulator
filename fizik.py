"""
Su altı aracının hareket denklemleri (Fossen modeli, 4 serbestlik derecesi).

Durum vektörü:  [x, y, z, psi, u, v, w, r]
  x, y, z : konum (m), dünya ekseninde. z = derinlik (aşağı pozitif)
  psi     : baş açısı (rad)
  u, v, w : ileri, yan, dikey hız (m/s), ARACIN KENDİ EKSENİNDE (yere göre)
  r       : dönüş hızı (rad/s)

Kuvvet vektörü (gövde ekseninde):  [F_ileri, F_yan, F_dikey, tork]

Hareket denklemi (akıntıya göre bağıl hız ile):
  M * (bağıl ivme) = itki - Coriolis - sürtünme - (ağırlık - kaldırma)
"""
import math
import numpy as np

import ayarlar as A

# Etkin kütleler: aracın kendi kütlesi + sürüklediği su
M = np.array([
    A.KUTLE + A.EK_KUTLE_ILERI,     # ileri:  17.0 kg
    A.KUTLE + A.EK_KUTLE_YAN,       # yan:    24.2 kg
    A.KUTLE + A.EK_KUTLE_DIKEY,     # dikey:  26.1 kg
    A.ATALET + A.EK_ATALET,         # dönüş:  0.28 kg·m²
])


def surtunme(hiz, k):
    """Doğrusal + karesel sürtünme kuvveti (harekete ters yönde)."""
    return k[0] * hiz + k[1] * hiz * abs(hiz)


def turev(durum, kuvvet, akinti):
    """Durumun zamana göre türevi."""
    x, y, z, psi, u, v, w, r = durum
    akx, aky = akinti
    c, s = math.cos(psi), math.sin(psi)

    # 1) Kinematik: aracın kendi eksenindeki hızını dünya eksenine çevir
    x_t = c * u - s * v
    y_t = s * u + c * v
    z_t = w
    psi_t = r

    # 2) Akıntıyı aracın eksenine çevir ve suya göre (bağıl) hızı bul
    uc = c * akx + s * aky
    vc = -s * akx + c * aky
    ub, vb, wb = u - uc, v - vc, w

    # 3) Coriolis / merkezcil terimler: eksen araçla birlikte döndüğü için oluşur.
    #    Dönerken savrulmanın sebebi budur.
    coriolis = np.array([
        -A.KUTLE * vb * r,
        A.KUTLE * ub * r,
        0.0,
        0.0,
    ])

    # 4) Sürtünme (suya göre hıza bağlı)
    surt = np.array([
        surtunme(ub, A.K_ILERI),
        surtunme(vb, A.K_YAN),
        surtunme(wb, A.K_DIKEY),
        surtunme(r, A.K_DONUS),
    ])

    # 5) Ağırlık - kaldırma (sadece dikey)
    net_agirlik = np.array([0.0, 0.0, A.AGIRLIK - A.KALDIRMA, 0.0])

    # 6) Newton: bağıl ivme = toplam kuvvet / etkin kütle
    bagil_ivme = (np.array(kuvvet) - coriolis - surt + net_agirlik) / M

    # 7) Akıntı dünyada sabit olsa da araç dönünce aracın ekseninde farklı görünür
    akinti_degisimi = np.array([r * vc, -r * uc, 0.0, 0.0])

    ivme = bagil_ivme + akinti_degisimi
    return np.array([x_t, y_t, z_t, psi_t, *ivme])


def sinirlari_uygula(durum):
    """Su yüzeyi ve deniz tabanı sınırları."""
    if durum[2] < 0.0:
        durum[2] = 0.0
        durum[6] = max(durum[6], 0.0)
    elif durum[2] > A.MAX_DERINLIK:
        durum[2] = A.MAX_DERINLIK
        durum[6] = min(durum[6], 0.0)
    return durum


def rk4_adim(durum, kuvvet, akinti, dt):
    """4. derece Runge-Kutta ile bir zaman adımı ilerler."""
    k1 = turev(durum, kuvvet, akinti)
    k2 = turev(durum + 0.5 * dt * k1, kuvvet, akinti)
    k3 = turev(durum + 0.5 * dt * k2, kuvvet, akinti)
    k4 = turev(durum + dt * k3, kuvvet, akinti)
    yeni = durum + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    yeni[3] = (yeni[3] + math.pi) % (2 * math.pi) - math.pi   # açıyı -180..180 aralığında tut
    return sinirlari_uygula(yeni)
