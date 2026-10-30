"""MEB Destek Hizmetleri Genel Müdürlüğü öğretmenevi listesi.

Sayfa yapısı değişebileceği için tablo sütunları başlık metninden bulunur.
Sayfa il seçimiyle (ASP.NET postback) çalışıyorsa her il için ayrıca istenir.
Ayrıştırma başarısız olursa hata fırlatılır; bu durumda çalıştırıcı bu
kaynağı atlar ve hiçbir tesisi "kapandı" olarak işaretlemez.
"""
import time

import requests
from bs4 import BeautifulSoup

from pipeline.model import anahtar_metin, kayit, temizle

KOD = "meb_dhgm"
URL = "https://dhgm.meb.gov.tr/edestek/ogretmenevi/ogretmenevi_liste.aspx"
BAKANLIK = "Millî Eğitim Bakanlığı"
BIRIM = "Bakanlık (Merkez) - Öğretmenevi Ağı (Tam Liste)"
EN_AZ_KAYIT = 300  # bundan az kayıt gelirse sayfa yapısı değişmiş sayılır

BASLIK_ESLEME = [
    ("ilce", ("ilce",)),
    ("il", ("il", "sehir")),
    ("telefon", ("telefon", "tel")),
    ("adres", ("adres",)),
    ("tesisAdi", ("ogretmenevi", "adi", "kurum", "tesis")),
]

oturum = requests.Session()
oturum.headers["User-Agent"] = "kamu-misafirhaneleri-bot/1.0 (+https://github.com)"


def _sutun_esle(basliklar):
    esleme = {}
    for i, b in enumerate(anahtar_metin(h) for h in basliklar):
        for alan, kelimeler in BASLIK_ESLEME:
            if alan not in esleme and any(b == k or b.startswith(k + " ") or k in b.split() for k in kelimeler):
                esleme[alan] = i
                break
    return esleme if {"il", "tesisAdi"} <= esleme.keys() else None


def _tablolari_ayristir(soup, varsayilan_il=""):
    sonuc = []
    for tablo in soup.find_all("table"):
        if tablo.find("table"):
            continue  # dış çerçeve tablosu; satırları iç tablodan okunur
        satirlar = tablo.find_all("tr")
        if len(satirlar) < 2:
            continue
        basliklar = [c.get_text(" ", strip=True) for c in satirlar[0].find_all(["th", "td"])]
        esleme = _sutun_esle(basliklar)
        if not esleme and varsayilan_il:
            esleme = _sutun_esle(basliklar + ["il"])
        if not esleme:
            continue
        for tr in satirlar[1:]:
            hucre = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
            if len(hucre) < 2:
                continue
            al = lambda a: hucre[esleme[a]] if a in esleme and esleme[a] < len(hucre) else ""
            ad = temizle(al("tesisAdi"))
            if not ad:
                continue
            sonuc.append(kayit(
                bakanlik=BAKANLIK, birim=BIRIM,
                il=temizle(al("il")) or varsayilan_il, ilce=al("ilce"),
                tesisAdi=ad, adres=al("adres"), telefon=al("telefon"),
                kaynakUrl=URL + " (RESMİ)", kaynakKodu=KOD,
                dogrulama="OTOMATİK - DHGM resmi listesinden çekildi",
            ))
    return sonuc


def _form_verisi(soup):
    return {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden][name]")}


def topla():
    yanit = oturum.get(URL, timeout=60)
    yanit.raise_for_status()
    soup = BeautifulSoup(yanit.text, "lxml")
    kayitlar = _tablolari_ayristir(soup)

    # Liste il seçimine bağlıysa her il için postback gönder
    secim = next((s for s in soup.find_all("select") if len(s.find_all("option")) >= 70), None)
    if len(kayitlar) < EN_AZ_KAYIT and secim is not None:
        kayitlar = []
        for opt in secim.find_all("option"):
            deger, il = opt.get("value", ""), temizle(opt.get_text())
            if not deger or deger in ("0", "-1"):
                continue
            veri = _form_verisi(soup) | {secim["name"]: deger, "__EVENTTARGET": secim["name"]}
            r = oturum.post(URL, data=veri, timeout=60)
            r.raise_for_status()
            kayitlar += _tablolari_ayristir(BeautifulSoup(r.text, "lxml"), varsayilan_il=il)
            time.sleep(1)

    tekil = {k["tesisId"]: k for k in kayitlar}
    if len(tekil) < EN_AZ_KAYIT:
        raise RuntimeError(f"DHGM sayfasından yalnızca {len(tekil)} kayıt çıktı; sayfa yapısı değişmiş olabilir")
    return list(tekil.values())
