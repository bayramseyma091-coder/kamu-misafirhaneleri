"""Elle tutulan Excel listesi (data/kaynak/kamu_misafirhaneleri.xlsx).

Bu dosya güncellenip depoya gönderildiğinde değişiklikler otomatik yayınlanır.
"""
from pathlib import Path

import openpyxl

from pipeline.model import kayit, temizle

KOD = "manuel"
DOSYA = Path(__file__).resolve().parents[2] / "data" / "kaynak" / "kamu_misafirhaneleri.xlsx"

# Tesis olmayan (araştırma notu) satırlar
ATLANACAK_AD = ("VERİ BULAMADIM", "GEÇERSİZ BİRİM")

SUTUNLAR = {
    "BAKANLIK": "bakanlik",
    "BİRİM": "birim",
    "İL": "il",
    "İLÇE": "ilce",
    "MİSAFİRHANE ADI": "tesisAdi",
    "ADRES": "adres",
    "TELEFON": "telefon",
    "KAYNAK": "kaynakUrl",
    "RESMİ DOĞRULAMA": "dogrulama",
    "NOT": "not",
}


def topla():
    ws = openpyxl.load_workbook(DOSYA, read_only=True).active
    satirlar = ws.iter_rows(values_only=True)
    basliklar = [temizle(h).upper() for h in next(satirlar)]
    sonuc = []
    for satir in satirlar:
        ham = {SUTUNLAR[b]: v for b, v in zip(basliklar, satir) if b in SUTUNLAR}
        ad = temizle(ham.get("tesisAdi"))
        if not ad or ad.upper().startswith(ATLANACAK_AD):
            continue
        sonuc.append(kayit(**ham, kaynakKodu=KOD))
    return sonuc
