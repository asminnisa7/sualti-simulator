"""
Sensör modelleri: gerçek değeri belirli sıklıkta, gürültü ekleyerek ölçer.
Araç yazılımı (otopilot, tahmin) gerçek değeri hiçbir zaman göremez,
yalnızca bu ölçümleri görür.
"""
import math
import random

import ayarlar as A


class Sensor:
    """Belirli sıklıkta ölçüm yapan, gürültülü bir sensör."""

    def __init__(self, siklik, gurultu, kayma=0.0):
        self.periyot = 1.0 / siklik
        self.gurultu = gurultu
        self.kayma = kayma
        self.sayac = 0.0
        self.son = None            # son ölçüm

    def adim(self, gercek, dt, ideal=False):
        """Ölçüm zamanı geldiyse yeni ölçüm yapar ve onu döndürür, gelmediyse None."""
        self.sayac += dt
        if self.sayac + 1e-9 < self.periyot:
            return None
        self.sayac -= self.periyot
        if ideal:
            self.son = gercek
        else:
            self.son = gercek + self.kayma + random.gauss(0.0, self.gurultu)
        return self.son


class KapiKamerasi:
    """
    Önündeki kapıyı gören kamera. Görüntü işlemenin sonucunu taklit eder: kapı görüş
    alanı ve menzil içindeyse kapı merkezinin araca göre konumunu (ileri, yan) ölçer.
    Ölçüm hatası mesafeyle artar.
    """

    def __init__(self):
        self.periyot = 1.0 / A.KAMERA_SIKLIK
        self.sayac = 0.0

    def olc(self, durum, kapi, kapi_no, dt, ideal=False):
        self.sayac += dt
        if self.sayac + 1e-9 < self.periyot:
            return None
        self.sayac -= self.periyot
        dx, dy = kapi.x - durum[0], kapi.y - durum[1]
        mesafe = math.hypot(dx, dy)
        c, s = math.cos(durum[3]), math.sin(durum[3])
        ileri, yan = c * dx + s * dy, -s * dx + c * dy
        if mesafe > A.KAMERA_MENZIL or ileri < 0.3 or \
                abs(math.degrees(math.atan2(yan, ileri))) > A.KAMERA_GORUS / 2:
            return None                                   # kapı görünmüyor
        if not ideal:
            sigma = A.KAMERA_GURULTU * mesafe
            ileri += random.gauss(0.0, sigma)
            yan += random.gauss(0.0, sigma)
        return kapi_no, ileri, yan


class Sensorler:
    def __init__(self):
        self.ideal = False         # True: gürültüsüz ve kaymasız sensörler (karşılaştırma için)
        self.derinlik = Sensor(*A.DERINLIK_SENSORU)
        self.pusula = Sensor(A.PUSULA[0], math.radians(A.PUSULA[1]))
        self.jiroskop = Sensor(*A.JIROSKOP, kayma=A.JIROSKOP_KAYMA)
        self.dvl_u = Sensor(*A.DVL)
        self.dvl_v = Sensor(*A.DVL)
        self.kamera = KapiKamerasi()

    def kapi_olc(self, durum, gorev, dt):
        """Sıradaki kapıyı kamerayla görmeye çalışır: (kapı no, ileri, yan) ya da None."""
        if gorev.bitti:
            return None
        return self.kamera.olc(durum, gorev.kapilar[gorev.siradaki], gorev.siradaki, dt, self.ideal)

    def olc(self, durum, dt):
        """Tüm sensörleri bir adım ilerletir. Yeni ölçümleri sözlük olarak döndürür
        (o adımda ölçüm yapmayan sensörün değeri None olur)."""
        x, y, z, psi, u, v, w, r = durum
        i = self.ideal
        return {
            "derinlik": self.derinlik.adim(z, dt, i),
            "pusula": self.pusula.adim(psi, dt, i),
            "jiroskop": self.jiroskop.adim(r, dt, i),
            "dvl_u": self.dvl_u.adim(u, dt, i),
            "dvl_v": self.dvl_v.adim(v, dt, i),
        }
