"""Aracın ve simülasyonun tüm sayısal parametreleri."""

# --- Kütle ve atalet ---
KUTLE = 11.5            # kg
G = 9.81                # m/s²
AGIRLIK = KUTLE * G     # N  (112.8)
KALDIRMA = 114.8        # N  (ağırlıktan biraz fazla: hafif pozitif yüzer)
ATALET = 0.16           # kg·m²  (dönmeye karşı direnç)

# --- Eklenmiş kütle: hızlanırken araçla birlikte sürüklenen su ---
EK_KUTLE_ILERI = 5.5    # kg
EK_KUTLE_YAN = 12.7     # kg   (yandan daha geniş: daha çok su sürüklenir)
EK_KUTLE_DIKEY = 14.57  # kg
EK_ATALET = 0.12        # kg·m²

# --- Sürtünme katsayıları: (doğrusal, karesel) ---
K_ILERI = (4.0, 18.0)
K_YAN = (6.2, 21.7)
K_DIKEY = (5.2, 37.0)
K_DONUS = (0.07, 1.55)

# --- Pilot komutu: %100 güçte istenen en büyük kuvvetler ---
#              [ileri (N), yan (N), dikey (N), dönüş torku (N·m)]
ISTENEN_MAX = [80.0, 80.0, 80.0, 6.0]

# --- Motorlar (iticiler) ---
ITICI_ILERI_MAX = 50.0      # N  (pervane ileri yönde daha güçlü)
ITICI_GERI_MAX = 40.0       # N
ITICI_ZAMAN_SABITI = 0.1    # s  (motorun tam güce çıkma gecikmesi)

# Her motor: (ad, x konumu, y konumu, itki açısı (derece), dikey mi?)
# Konumlar gövde ekseninde, metre: x ileri, y sağa.
# Açı: motorun aracı ittiği yön, 0° = ileri, pozitif = sağa doğru.
ITICILER = [
    ("T1 ön-sağ",    0.156,  0.111,  -45.0, False),
    ("T2 ön-sol",    0.156, -0.111,   45.0, False),
    ("T3 arka-sağ", -0.156,  0.111, -135.0, False),
    ("T4 arka-sol", -0.156, -0.111,  135.0, False),
    ("T5 dikey-sağ", 0.0,    0.218,    0.0, True),
    ("T6 dikey-sol", 0.0,   -0.218,    0.0, True),
]

# --- Görev havuzu ---
HAVUZ_UZUNLUK = 50.0    # m (x yönü)
HAVUZ_GENISLIK = 25.0   # m (y yönü)
MAX_DERINLIK = 5.0      # m (havuz derinliği)
ARAC_YARICAP = 0.3      # m (çarpışma hesabı için)
BASLANGIC = (3.0, 12.5, 1.0)   # aracın başlangıç konumu: x, y, derinlik

# Kapılar: (merkez x, merkez y, geçiş yönü (derece), genişlik, en sığ, en derin)
# Geçiş yönü: 0° = sağa (+x), 90° = aşağı (+y), 180° = sola, 270° = yukarı
KAPILAR = [
    (10.0, 12.5,   0.0, 2.5, 0.5, 2.5),
    (18.0, 19.0,   0.0, 2.0, 1.0, 3.0),
    (28.0,  7.0,   0.0, 2.0, 2.0, 4.0),
    (40.0, 12.5,  90.0, 2.0, 1.0, 3.0),
    (30.0, 21.0, 180.0, 1.5, 0.5, 2.0),
]

# Engeller (havuz tabanından yüzeye uzanan sütunlar): (x, y, yarıçap)
ENGELLER = [
    (14.0,  8.0, 0.6),
    (24.0, 13.0, 0.8),
    (35.0, 18.0, 0.7),
    (45.0,  6.0, 0.5),
]

# --- Simülasyon ---
DT = 0.01               # fizik adımı: 0.01 s (saniyede 100 hesap)

# --- Otopilot (PID kazançları) ---
BAS_KP, BAS_KI, BAS_KD = 6.0, 0.4, 1.8                  # baş açısı (çıkış: tork)
DERINLIK_KP, DERINLIK_KI, DERINLIK_KD = 60.0, 6.0, 40.0 # derinlik (çıkış: dikey kuvvet)

# --- Gerçekçi akıntı ---
AKINTI_DERIN_AZALMA = 0.5   # en dipte akıntı yüzeydekinin %50'sine düşer
TURB_SIDDET = 0.3           # dalgalanma şiddeti (ortalama akıntı hızının oranı)
TURB_ZAMAN = 3.0            # s, dalgalanmaların ortalama süresi
TURB_EN_AZ = 0.03           # m/s, akıntı çok zayıfken bile küçük dalgalanma

# --- Batarya ve güç ---
BATARYA_AH = 18.0           # Ah (BlueROV2 benzeri 4S lityum batarya)
V_DOLU = 16.8               # V  (hücre başına 4.2 V)
V_BOS = 12.8                # V  (hücre başına 3.2 V)
V_NOMINAL = 14.8            # V
IC_DIRENC = 0.02            # Ω  (yük altında voltaj düşümü)
ELEKTRONIK_GUC = 15.0       # W  (kamera, bilgisayar, sensörler)
V_ITKI_REF = 16.0           # V  (motor itki değerlerinin verildiği voltaj)
SU_YOGUNLUGU = 1000.0       # kg/m³
PERVANE_ALANI = 0.00454     # m²  (76 mm çaplı pervane)
ITICI_VERIM = 0.35          # pervane + motor + sürücü toplam verimi

# --- Sensörler: (ölçüm sıklığı Hz, gürültü standart sapması) ---
DERINLIK_SENSORU = (10.0, 0.02)     # m      (basınç sensörü)
PUSULA = (10.0, 2.0)                # derece
JIROSKOP = (100.0, 0.01)            # rad/s
JIROSKOP_KAYMA = 0.005              # rad/s  (sabit hata, ~0.3°/s)
DVL = (5.0, 0.01)                   # m/s    (Doppler hız ölçer)

# --- Tahmin (kestirim) ---
KALMAN_IVME_GURULTUSU = 0.5         # m/s²   (aracın ne kadar ani hızlanabileceği varsayımı)
PUSULA_DUZELTME = 0.02              # tamamlayıcı filtre: her pusula ölçümünde düzeltme oranı
KAYMA_OGRENME = 0.002               # jiroskop kaymasını öğrenme hızı

# --- Kapı kamerası (görüntü işlemeyle kapı tespiti) ---
KAMERA_SIKLIK = 10.0        # Hz
KAMERA_MENZIL = 6.0         # m   (su altında görüş mesafesi)
KAMERA_GORUS = 80.0         # derece (yatay görüş açısı)
KAMERA_GURULTU = 0.03       # ölçüm hatası: mesafenin %3'ü (standart sapma)
KAPI_DUZELTME = 0.05        # her kapı ölçümünde konum tahmininin düzeltme oranı
