"""Ortak veri modeli.

Alan adları TUCBS "Kamu Hizmetleri / Yapı" temalarındaki tesis nesnelerine
yakın tutulmuştur; tam şema eşlemesi 3. aşamada yapılacaktır.
"""
import hashlib
import re
import unicodedata

# Kayıt alanları (sıra GeoJSON properties ve CSV çıktısında korunur)
ALANLAR = [
    "tesisId",        # kalıcı kimlik (bakanlık+il+ilçe+ad özetinden)
    "tesisAdi",
    "bakanlik",
    "birim",
    "il",
    "ilce",
    "adres",
    "telefon",
    "kaynakUrl",
    "kaynakKodu",     # verinin geldiği toplayıcı (manuel, meb_dhgm ...)
    "dogrulama",
    "not",
    "konumKaynagi",   # adres / ilce / il / yok
]

# Değişiklik karşılaştırmasında dikkate alınan alanlar
IZLENEN_ALANLAR = ["tesisAdi", "birim", "il", "ilce", "adres", "telefon"]

BOS_DEGERLER = {"", "-", "—", "none", "null"}


def temizle(deger):
    if deger is None:
        return ""
    s = re.sub(r"\s+", " ", str(deger)).strip()
    return "" if s.lower() in BOS_DEGERLER else s


def anahtar_metin(s):
    """Kimlik üretimi için büyük/küçük harf, aksan ve noktalamadan bağımsız metin."""
    s = temizle(s).replace("İ", "i").replace("I", "ı").lower()
    s = unicodedata.normalize("NFKD", s.replace("ı", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def tesis_id(bakanlik, il, ilce, ad):
    ham = "|".join(anahtar_metin(x) for x in (bakanlik, il, ilce, ad))
    return "KM-" + hashlib.sha1(ham.encode()).hexdigest()[:10].upper()


def kayit(**alanlar):
    r = {a: temizle(alanlar.get(a)) for a in ALANLAR}
    if not r["tesisId"]:
        r["tesisId"] = tesis_id(r["bakanlik"], r["il"], r["ilce"], r["tesisAdi"])
    return r
