"""
Gerçekçi akıntı modeli:
  - Kullanıcının ayarladığı ortalama hız ve yön
  - Derinlikle zayıflama (yüzeyde güçlü, dipte zayıf)
  - Türbülans: birinci derece Gauss-Markov süreci
        d(dalga)/dt = -dalga / T + gürültü
    Akıntı rastgele değişir ama sıçramaz; değişimler yaklaşık T saniye sürer.
"""
import math
import random

import ayarlar as A


class Akinti:
    def __init__(self):
        self.acik = False
        self.hiz = 0.3            # m/s (ortalama, yüzeyde)
        self.yon = 90.0           # derece (akıntının aktığı yön)
        self.turbulans = True
        self.dalga_x = 0.0        # türbülans bileşenleri (m/s)
        self.dalga_y = 0.0

    def adim(self, dt):
        """Türbülansı bir zaman adımı ilerletir."""
        if not (self.acik and self.turbulans):
            self.dalga_x = self.dalga_y = 0.0
            return
        sigma = max(A.TURB_EN_AZ, A.TURB_SIDDET * self.hiz)    # dalgalanmanın standart sapması
        a = math.exp(-dt / A.TURB_ZAMAN)
        b = sigma * math.sqrt(1.0 - a * a)
        self.dalga_x = a * self.dalga_x + b * random.gauss(0.0, 1.0)
        self.dalga_y = a * self.dalga_y + b * random.gauss(0.0, 1.0)

    def hiz_vektoru(self, z):
        """z derinliğindeki akıntı hızı (vx, vy), dünya ekseninde."""
        if not self.acik:
            return (0.0, 0.0)
        carpan = 1.0 - A.AKINTI_DERIN_AZALMA * min(1.0, z / A.MAX_DERINLIK)
        a = math.radians(self.yon)
        return (carpan * (self.hiz * math.cos(a) + self.dalga_x),
                carpan * (self.hiz * math.sin(a) + self.dalga_y))
