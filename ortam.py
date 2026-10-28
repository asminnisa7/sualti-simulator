"""
Görev ortamı: havuz duvarları, engeller, çarpışmalar ve kapı görevi.
"""
import math

import ayarlar as A


# ------------------------------------------------------------------ #
# Çarpışmalar
# ------------------------------------------------------------------ #
def _dunya_hizi(durum):
    c, s = math.cos(durum[3]), math.sin(durum[3])
    u, v = durum[4], durum[5]
    return c * u - s * v, s * u + c * v


def _govde_hizi_yaz(durum, vx, vy):
    c, s = math.cos(durum[3]), math.sin(durum[3])
    durum[4] = c * vx + s * vy
    durum[5] = -s * vx + c * vy


def _duvara_dogru_hizi_sil(durum, nx, ny):
    """(nx, ny): duvardan araca doğru birim vektör. Araç duvara doğru gidiyorsa
    o yöndeki hızını sıfırla (çarpıp durma), duvara paralel kaymasına izin ver."""
    vx, vy = _dunya_hizi(durum)
    dik = vx * nx + vy * ny
    if dik < 0:
        vx -= dik * nx
        vy -= dik * ny
        _govde_hizi_yaz(durum, vx, vy)


def carpismalari_uygula(durum):
    """Duvar ve engel çarpışmalarını uygular. Çarpışma olduysa True döner."""
    R = A.ARAC_YARICAP
    carpti = False

    # Havuz duvarları
    if durum[0] < R:
        durum[0] = R
        _duvara_dogru_hizi_sil(durum, 1, 0)
        carpti = True
    elif durum[0] > A.HAVUZ_UZUNLUK - R:
        durum[0] = A.HAVUZ_UZUNLUK - R
        _duvara_dogru_hizi_sil(durum, -1, 0)
        carpti = True
    if durum[1] < R:
        durum[1] = R
        _duvara_dogru_hizi_sil(durum, 0, 1)
        carpti = True
    elif durum[1] > A.HAVUZ_GENISLIK - R:
        durum[1] = A.HAVUZ_GENISLIK - R
        _duvara_dogru_hizi_sil(durum, 0, -1)
        carpti = True

    # Sütunlar
    for ex, ey, er in A.ENGELLER:
        dx, dy = durum[0] - ex, durum[1] - ey
        mesafe = math.hypot(dx, dy)
        en_az = er + R
        if 1e-9 < mesafe < en_az:
            nx, ny = dx / mesafe, dy / mesafe
            durum[0] = ex + nx * en_az          # aracı sütunun dışına it
            durum[1] = ey + ny * en_az
            _duvara_dogru_hizi_sil(durum, nx, ny)
            carpti = True
    return carpti


# ------------------------------------------------------------------ #
# Kapılar
# ------------------------------------------------------------------ #
class Kapi:
    def __init__(self, x, y, yon_derece, genislik, sig, derin):
        self.x, self.y = x, y
        self.yon = math.radians(yon_derece)
        self.genislik = genislik
        self.sig, self.derin = sig, derin
        self.dx, self.dy = math.cos(self.yon), math.sin(self.yon)   # geçiş yönü
        self.px, self.py = -self.dy, self.dx                        # kapı çizgisi yönü

    def direkler(self):
        h = self.genislik / 2
        return ((self.x - h * self.px, self.y - h * self.py),
                (self.x + h * self.px, self.y + h * self.py))

    def ileri_mesafe(self, x, y):
        """Kapı çizgisine geçiş yönünde işaretli uzaklık (önce -, geçince +)."""
        return (x - self.x) * self.dx + (y - self.y) * self.dy

    def yan_mesafe(self, x, y):
        return (x - self.x) * self.px + (y - self.y) * self.py


class Gorev:
    def __init__(self):
        self.kapilar = [Kapi(*k) for k in A.KAPILAR]
        self.sifirla()

    def sifirla(self):
        self.siradaki = 0
        self.sure = 0.0
        self.basladi = False
        self.bitti = False
        self.carpisma_sayisi = 0
        self._carpiyordu = False
        self._onceki = None
        self.mesaj = ""
        self.mesaj_suresi = 0.0

    def _mesaj(self, metin, sure=3.0):
        self.mesaj = metin
        self.mesaj_suresi = sure

    def guncelle(self, durum, carpti, dt):
        x, y, z = durum[0], durum[1], durum[2]
        hiz = math.hypot(durum[4], durum[5])

        if not self.basladi and hiz > 0.05:
            self.basladi = True
        if self.basladi and not self.bitti:
            self.sure += dt
        if self.mesaj_suresi > 0:
            self.mesaj_suresi -= dt

        # Çarpışmayı yalnızca başladığı anda say (temas sürerken tekrar sayma)
        if carpti and not self._carpiyordu:
            self.carpisma_sayisi += 1
        self._carpiyordu = carpti

        # Sıradaki kapıdan geçildi mi?
        if self._onceki is not None and not self.bitti:
            k = self.kapilar[self.siradaki]
            once = k.ileri_mesafe(*self._onceki)
            simdi = k.ileri_mesafe(x, y)
            if once < 0 <= simdi and abs(k.yan_mesafe(x, y)) < k.genislik / 2:
                if k.sig <= z <= k.derin:
                    self.siradaki += 1
                    if self.siradaki == len(self.kapilar):
                        self.bitti = True
                        self._mesaj(f"GÖREV TAMAM!  Süre: {sure_yazisi(self.sure)}  "
                                    f"Çarpışma: {self.carpisma_sayisi}", 8.0)
                    else:
                        self._mesaj(f"Kapı {self.siradaki} geçildi!  {sure_yazisi(self.sure)}")
                else:
                    self._mesaj(f"Kapı {self.siradaki + 1}: yanlış derinlik! "
                                f"{k.sig:.1f}-{k.derin:.1f} m arasında geç")
        self._onceki = (x, y)


def sure_yazisi(saniye):
    dk = int(saniye // 60)
    return f"{dk:02d}:{saniye - dk * 60:04.1f}"
