"""Onaylanan GitHub bildirimini data/duzeltmeler.json dosyasına işler.

Kullanım (GitHub Actions):  python -m pipeline.duzeltme "$GITHUB_EVENT_PATH"

Dosya yapısı:
  degistir: {tesisId: {alan: değer}}   resmî kaynaktaki değerin üzerine yazılır
  kapat:    {tesisId: {issue, tarih}}  listeden çıkarılır ("kapandı" olarak yayınlanır)
  ekle:     [kayıt, ...]               listeye eklenir ("yeni" olarak yayınlanır)
"""
import json
import re
import sys
from pathlib import Path

from pipeline.model import kayit, temizle

KOK = Path(__file__).resolve().parents[1]
DOSYA = KOK / "data" / "duzeltmeler.json"
ANLIK = KOK / "data" / "misafirhaneler.geojson"
HATA = "⚠️ Uygulanmadı: "
DEGISEBILIR = ["tesisAdi", "il", "ilce", "adres", "telefon"]
ETIKETLER = {  # form başlığı → alan
    "Bildirim türü": "tur", "Tesis kodu": "tesis_id", "Tesis adı": "tesisAdi", "Bağlı olduğu bakanlık": "bakanlik",
    "İl": "il", "İlçe": "ilce", "Adres": "adres", "Telefon": "telefon", "Kaynak bağlantısı": "kaynak", "Açıklama": "aciklama",
}


def yukle():
    return json.loads(DOSYA.read_text()) if DOSYA.exists() else {"degistir": {}, "kapat": {}, "ekle": []}


def uygula(yeni, duz=None):
    """run.py tarafından toplanan kayıtlara düzeltmeleri uygular (yerinde)."""
    duz = duz or yukle()
    for tid, alanlar in duz.get("degistir", {}).items():
        if tid in yeni:
            yeni[tid].update({a: v for a, v in alanlar.items() if a in DEGISEBILIR})
    for tid in duz.get("kapat", {}):
        yeni.pop(tid, None)
    for k in duz.get("ekle", []):
        yeni.setdefault(k["tesisId"], dict(k))


def formu_ayristir(govde):
    alanlar = {}
    for baslik, deger in re.findall(r"^### (.+?)\s*\n+(.*?)(?=^### |\Z)", govde or "", flags=re.M | re.S):
        deger = deger.strip()
        if baslik.strip() in ETIKETLER and deger != "_No response_":
            alanlar[ETIKETLER[baslik.strip()]] = temizle(deger)
    return alanlar


def isle(olay):
    issue = olay["issue"]
    form = formu_ayristir(issue.get("body"))
    tur, tid = form.get("tur", ""), form.get("tesis_id", "")
    mevcut = {f["properties"]["tesisId"]: f["properties"] for f in json.loads(ANLIK.read_text())["features"]}
    duz = yukle()
    ref = {"issue": issue["number"], "tarih": issue.get("updated_at", "")}

    if tur.startswith("Yeni tesis"):
        if not (form.get("tesisAdi") and form.get("il")):
            return HATA + "Yeni tesis için en az tesis adı ve il gerekli."
        k = kayit(bakanlik=form.get("bakanlik"), tesisAdi=form["tesisAdi"], il=form["il"], ilce=form.get("ilce"),
                  adres=form.get("adres"), telefon=form.get("telefon"), kaynakUrl=form.get("kaynak") or issue["html_url"],
                  kaynakKodu="bildirim", dogrulama=f"Kullanıcı bildirimi, yönetici onaylı (#{issue['number']})")
        if k["tesisId"] in mevcut:
            return HATA + f"Bu tesis zaten listede: {k['tesisId']}"
        duz["ekle"] = [e for e in duz.get("ekle", []) if e["tesisId"] != k["tesisId"]] + [k]
        sonuc = f"Yeni tesis eklendi: {k['tesisAdi']} ({k['il']})"
    elif tid not in mevcut:
        return HATA + f"Tesis kodu bulunamadı: '{tid}'. Kodu tesis sayfasından kontrol edin."
    elif tur.startswith("Tesis kapandı"):
        duz.setdefault("kapat", {})[tid] = ref
        sonuc = f"Tesis kapandı olarak işaretlendi: {mevcut[tid]['tesisAdi']}"
    else:
        farklar = {a: form[a] for a in DEGISEBILIR if form.get(a) and form[a] != mevcut[tid].get(a, "")}
        if not farklar:
            return HATA + "Formdaki bilgiler mevcut kayıtla aynı; değişiklik yapılmadı."
        duz.setdefault("degistir", {}).setdefault(tid, {}).update(farklar)
        sonuc = "Güncellenen alanlar: " + ", ".join(f"{a} → {v}" for a, v in farklar.items())

    DOSYA.write_text(json.dumps(duz, ensure_ascii=False, indent=1) + "\n")
    return sonuc


if __name__ == "__main__":
    mesaj = isle(json.loads(Path(sys.argv[1]).read_text()))
    print(mesaj)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(mesaj)
