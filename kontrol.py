"""
Otopilot: baş açısı sabitleme ve derinlik sabitleme (PID kontrol).
"""
import math

import ayarlar as A


def aci_farki(a):
    """Açı farkını -180°..+180° aralığına getirir (kısa yoldan dönmek için).
    Örneğin 350° -> 10° geçişinde 340° değil, 20° döner."""
    return (a + math.pi) % (2 * math.pi) - math.pi


class PID:
    def __init__(self, kp, ki, kd, cikis_siniri, integral_bolgesi):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.cikis_siniri = cikis_siniri
        self.integral_bolgesi = integral_bolgesi   # integral sadece bu hatadan küçükken toplanır
        self.integral = 0.0

    def sifirla(self):
        self.integral = 0.0

    def hesapla(self, hata, olcum_hizi, dt, ileri_besleme=0.0):
        """hata = hedef - ölçüm.
        Türev için hatanın değil ölçümün hızı kullanılır: hedef aniden değişince
        çıkış sıçramaz ("türev tekmesi" olmaz)."""
        if abs(hata) < self.integral_bolgesi:
            self.integral += hata * dt
            # integral tek başına çıkışın yarısını aşmasın
            sinir = 0.5 * self.cikis_siniri / max(self.ki, 1e-9)
            self.integral = max(-sinir, min(sinir, self.integral))
        cikis = ileri_besleme + self.kp * hata + self.ki * self.integral - self.kd * olcum_hizi
        return max(-self.cikis_siniri, min(self.cikis_siniri, cikis))


class Otopilot:
    def __init__(self):
        self.bas_acik = False
        self.derinlik_acik = False
        self.hedef_bas = 0.0
        self.hedef_derinlik = 0.0
        self.bas_pid = PID(A.BAS_KP, A.BAS_KI, A.BAS_KD,
                           cikis_siniri=A.ISTENEN_MAX[3], integral_bolgesi=math.radians(20))
        self.derinlik_pid = PID(A.DERINLIK_KP, A.DERINLIK_KI, A.DERINLIK_KD,
                                cikis_siniri=A.ISTENEN_MAX[2], integral_bolgesi=0.5)

    def bas_degistir(self, durum):
        self.bas_acik = not self.bas_acik
        self.hedef_bas = durum[3]
        self.bas_pid.sifirla()

    def derinlik_degistir(self, durum):
        self.derinlik_acik = not self.derinlik_acik
        self.hedef_derinlik = durum[2]
        self.derinlik_pid.sifirla()

    def kapat(self):
        self.bas_acik = self.derinlik_acik = False

    def uygula(self, istenen, pilot, durum, dt):
        """Pilotun istediği kuvvetleri, açık olan modlara göre düzenler.
        istenen: [ileri, yan, dikey, tork] ; pilot: tuşlardan gelen [-1, 0, 1] değerleri"""
        istenen = istenen.copy()
        z, psi, w, r = durum[2], durum[3], durum[6], durum[7]

        if self.bas_acik:
            if pilot[3] != 0:                       # pilot dönüyor: kontrol pilotta
                self.hedef_bas = psi
                self.bas_pid.sifirla()
            else:
                istenen[3] = self.bas_pid.hesapla(aci_farki(self.hedef_bas - psi), r, dt)

        if self.derinlik_acik:
            if pilot[2] != 0:                       # pilot dalıyor/çıkıyor
                self.hedef_derinlik = z
                self.derinlik_pid.sifirla()
            else:
                net_kaldirma = A.KALDIRMA - A.AGIRLIK   # bilinen yukarı kuvvet: baştan dengele
                istenen[2] = self.derinlik_pid.hesapla(self.hedef_derinlik - z, w, dt,
                                                       ileri_besleme=net_kaldirma)
        return istenen
