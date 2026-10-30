"""Değişiklik bildirimleri. Ayarlanmamış kanallar sessizce atlanır.

Telegram: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ortam değişkenleri
(GitHub'da Settings → Secrets and variables → Actions altına eklenir).
"""
import os
import sys

import requests

ETIKET = {"yeni": "🆕 Yeni açıldı", "guncellendi": "✏️ Güncellendi", "kapandi": "❌ Kapandı / listeden çıkarıldı"}
AZAMI_TEK_MESAJ = 15  # bundan fazla değişiklik varsa özet gönderilir
ALAN_ADI = {"tesisAdi": "Ad", "birim": "Birim", "il": "İl", "ilce": "İlçe", "adres": "Adres", "telefon": "Telefon"}


def metin(o):
    t = o["tesis"]
    satirlar = [f'{ETIKET[o["tur"]]}: {t["tesisAdi"]}',
                f'{t["il"]}{" / " + t["ilce"] if t["ilce"] else ""} · {t["bakanlik"]}']
    for alan, (eski, yeni) in o.get("farklar", {}).items():
        satirlar.append(f'{ALAN_ADI.get(alan, alan)}: {eski or "—"} → {yeni or "—"}')
    if o["tur"] != "kapandi" and t["telefon"]:
        satirlar.append(f'☎ {t["telefon"]}')
    return "\n".join(satirlar)


def _telegram(mesaj):
    token, sohbet = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and sohbet):
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": sohbet, "text": mesaj[:4000], "disable_web_page_preview": True},
                      timeout=30)
    if not r.ok:
        print(f"[UYARI] Telegram: {r.status_code} {r.text[:200]}", file=sys.stderr)


def gonder(olaylar):
    site = os.environ.get("SITE_URL", "")
    if len(olaylar) > AZAMI_TEK_MESAJ:
        sayac = {t: sum(o["tur"] == t for o in olaylar) for t in ETIKET}
        ozet = "\n".join(f"{ETIKET[t]}: {n}" for t, n in sayac.items() if n)
        _telegram(f"Kamu misafirhaneleri listesinde {len(olaylar)} değişiklik:\n{ozet}\n{site}degisiklikler.html")
        return
    for o in olaylar:
        _telegram(metin(o) + (f"\n{site}degisiklikler.html" if site else ""))
