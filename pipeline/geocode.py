"""Adres → koordinat (WGS84, EPSG:4326) dönüşümü.

OpenStreetMap Nominatim kullanılır (en fazla 1 istek/saniye kuralına uyulur).
Sonuçlar data/konum_onbellek.json dosyasında saklanır, böylece her adres
yalnızca bir kez sorgulanır. Adres bulunamazsa ilçe, o da yoksa il merkezi
kullanılır ve kaydın konumKaynagi alanına yazılır.
"""
import json
import os
import time
from pathlib import Path

import requests

DOSYA = Path(__file__).resolve().parents[1] / "data" / "konum_onbellek.json"
URL = "https://nominatim.openstreetmap.org/search"
AZAMI_SORGU = int(os.environ.get("AZAMI_KONUM_SORGUSU", "600"))


class Konumlayici:
    def __init__(self):
        self.onbellek = json.loads(DOSYA.read_text()) if DOSYA.exists() else {}
        self.sorgu_sayisi = 0
        self.oturum = requests.Session()
        self.oturum.headers["User-Agent"] = os.environ.get(
            "NOMINATIM_USER_AGENT", "kamu-misafirhaneleri/1.0")

    def _sorgula(self, metin):
        if metin in self.onbellek:
            return self.onbellek[metin]
        if self.sorgu_sayisi >= AZAMI_SORGU:
            return None  # sonraki çalıştırmada denenecek
        self.sorgu_sayisi += 1
        time.sleep(1.1)
        try:
            r = self.oturum.get(URL, params={"q": metin, "format": "json", "limit": 1,
                                             "countrycodes": "tr"}, timeout=30)
            r.raise_for_status()
            sonuc = r.json()
        except (requests.RequestException, ValueError):
            return None  # ağ hatası önbelleğe yazılmaz
        konum = [round(float(sonuc[0]["lon"]), 6), round(float(sonuc[0]["lat"]), 6)] if sonuc else []
        self.onbellek[metin] = konum
        return konum

    def konumla(self, k):
        denemeler = []
        if k["adres"]:
            denemeler.append(("adres", f'{k["adres"]}, {k["ilce"]}, {k["il"]}, Türkiye'))
        if k["ilce"]:
            denemeler.append(("ilce", f'{k["ilce"]}, {k["il"]}, Türkiye'))
        if k["il"]:
            denemeler.append(("il", f'{k["il"]}, Türkiye'))
        for tur, metin in denemeler:
            konum = self._sorgula(metin)
            if konum:
                return tur, konum
        return "yok", None

    def kaydet(self):
        DOSYA.write_text(json.dumps(self.onbellek, ensure_ascii=False, indent=0, sort_keys=True))
