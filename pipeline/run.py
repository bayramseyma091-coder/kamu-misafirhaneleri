"""Ana çalıştırıcı: topla → konumla → karşılaştır → kaydet → siteyi üret → bildir.

Kullanım:  python -m pipeline.run [--konumsuz] [--bildirimsiz]
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline import notify, site
from pipeline.geocode import Konumlayici
from pipeline.model import ALANLAR, IZLENEN_ALANLAR
from pipeline.sources import manuel, meb_dhgm

KOK = Path(__file__).resolve().parents[1]
VERI = KOK / "data"
ANLIK = VERI / "misafirhaneler.geojson"
GUNLUK = VERI / "degisiklikler.json"
DURUM = VERI / "durum.json"

# Sıra önemli: sonraki kaynak aynı tesisId için öncekinin yerine geçer
KAYNAKLAR = [manuel, meb_dhgm]
# Otomatik kaynak çalıştığında Excel'deki eşdeğer satırlar devre dışı kalır
DEVRALINAN = {meb_dhgm.KOD: lambda k: "dhgm.meb.gov.tr/edestek/ogretmenevi" in k["kaynakUrl"]}
# Kaynaktan önceki kaydın bu oranından azı gelirse kapanış bildirilmez
KAPANIS_ESIGI = 0.5


def yukle(yol, varsayilan):
    return json.loads(yol.read_text()) if yol.exists() else varsayilan


def yaz(yol, veri):
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n")


def calistir(konumla=True, bildir=True):
    simdi = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    onceki_anlik = yukle(ANLIK, {"features": []})
    onceki = {f["properties"]["tesisId"]: f for f in onceki_anlik["features"]}
    durum = yukle(DURUM, {"kaynaklar": {}})
    ilk_calisma = not onceki

    # 1) Topla
    yeni, basarili, sessiz = {}, set(), set()
    for kaynak in KAYNAKLAR:
        kd = durum["kaynaklar"].setdefault(kaynak.KOD, {})
        try:
            kayitlar = kaynak.topla()
        except Exception as e:  # kaynak hatası diğerlerini durdurmaz
            print(f"[UYARI] {kaynak.KOD}: {e}", file=sys.stderr)
            kd.update(son_hata=simdi, hata=str(e)[:300])
            if kd.get("son_basari") and kaynak.KOD in DEVRALINAN:
                yeni = {t: k for t, k in yeni.items() if not DEVRALINAN[kaynak.KOD](k)}
            # Önceki kayıtları olduğu gibi koru
            for tid, f in onceki.items():
                if f["properties"]["kaynakKodu"] == kaynak.KOD:
                    yeni[tid] = dict(f["properties"])
            continue
        basarili.add(kaynak.KOD)
        if kaynak.KOD in DEVRALINAN:
            devral = DEVRALINAN[kaynak.KOD]
            yeni = {t: k for t, k in yeni.items() if not devral(k)}
        if not kd.get("son_basari"):
            # Kaynağın ilk başarılı çalışması: mevcut verinin yerine geçer, bildirim üretmez
            sessiz |= {k["tesisId"] for k in kayitlar}
            sessiz |= {t for t, f in onceki.items() if DEVRALINAN.get(kaynak.KOD, lambda _: False)(f["properties"])}
        for k in kayitlar:
            yeni[k["tesisId"]] = k
        kd.update(son_basari=simdi, kayit_sayisi=len(kayitlar), hata=None)

    # 2) Konumla (önbellekli; sorgu sınırı dolarsa önceki konum korunur)
    konumlayici = Konumlayici() if konumla else None
    geometriler = {}
    for tid, k in yeni.items():
        eski = onceki.get(tid)
        tur, konum = konumlayici.konumla(k) if konumlayici else ("yok", None)
        if not konum and eski and eski.get("geometry"):
            tur, konum = eski["properties"].get("konumKaynagi", "yok"), eski["geometry"]["coordinates"]
        k["konumKaynagi"] = tur
        geometriler[tid] = {"type": "Point", "coordinates": konum} if konum else None
    if konumlayici:
        konumlayici.kaydet()

    # 3) Karşılaştır
    olaylar = []
    if not ilk_calisma:
        for tid, k in yeni.items():
            if tid in sessiz:
                continue
            if tid not in onceki:
                olaylar.append({"tur": "yeni", "tesis": k})
                continue
            eski = onceki[tid]["properties"]
            farklar = {a: [eski.get(a, ""), k[a]] for a in IZLENEN_ALANLAR if eski.get(a, "") != k[a]}
            if farklar:
                olaylar.append({"tur": "guncellendi", "tesis": k, "farklar": farklar})
        for tid, f in onceki.items():
            p = f["properties"]
            if tid in yeni or tid in sessiz or p["kaynakKodu"] not in basarili:
                continue
            onceki_sayi = sum(1 for g in onceki.values() if g["properties"]["kaynakKodu"] == p["kaynakKodu"])
            simdiki_sayi = sum(1 for g in yeni.values() if g["kaynakKodu"] == p["kaynakKodu"])
            if simdiki_sayi < onceki_sayi * KAPANIS_ESIGI:
                print(f"[UYARI] {p['kaynakKodu']}: kayıt sayısı {onceki_sayi}→{simdiki_sayi}, kapanışlar yok sayıldı",
                      file=sys.stderr)
                yeni[tid] = dict(p)
                geometriler[tid] = f.get("geometry")
                continue
            olaylar.append({"tur": "kapandi", "tesis": p})
    for o in olaylar:
        o["tarih"] = simdi

    # 4) Kaydet
    sirali = sorted(yeni.values(), key=lambda k: (k["il"], k["ilce"], k["bakanlik"], k["tesisAdi"]))
    yaz(ANLIK, {
        "type": "FeatureCollection",
        "name": "kamu_misafirhaneleri",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "guncelleme": simdi if (olaylar or ilk_calisma) else onceki_anlik.get("guncelleme", simdi),
        "features": [{"type": "Feature", "geometry": geometriler.get(k["tesisId"]),
                      "properties": {a: k[a] for a in ALANLAR}} for k in sirali],
    })
    with open(VERI / "misafirhaneler.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(ALANLAR + ["boylam", "enlem"])
        for k in sirali:
            g = geometriler.get(k["tesisId"])
            w.writerow([k[a] for a in ALANLAR] + (g["coordinates"] if g else ["", ""]))
    gunluk = olaylar[::-1] + yukle(GUNLUK, [])
    yaz(GUNLUK, gunluk[:5000])
    durum["son_calisma"] = simdi
    yaz(DURUM, durum)

    print(f"{len(sirali)} tesis | yeni {sum(o['tur'] == 'yeni' for o in olaylar)}, "
          f"güncellenen {sum(o['tur'] == 'guncellendi' for o in olaylar)}, "
          f"kapanan {sum(o['tur'] == 'kapandi' for o in olaylar)}")

    # 5) Siteyi üret ve bildir
    site.uret()
    if bildir and olaylar:
        notify.gonder(olaylar)
    return olaylar


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--konumsuz", action="store_true", help="koordinat sorgulamasını atla")
    p.add_argument("--bildirimsiz", action="store_true", help="Telegram vb. bildirim gönderme")
    a = p.parse_args()
    calistir(konumla=not a.konumsuz, bildir=not a.bildirimsiz)
