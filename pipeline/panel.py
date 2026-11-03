"""Yönetim paneli: özet göstergeler, dağılımlar, veri kalitesi, sistem durumu, yazdırılabilir rapor."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html import escape

from pipeline.model import anahtar_metin
from pipeline.sayfalar import gercek_tel, iskelet, kisa, slug

KAYNAK_ADI = {"manuel": "Excel listesi (elle güncellenen)", "meb_dhgm": "MEB DHGM öğretmenevi listesi (otomatik)",
              "bildirim": "Ziyaretçi bildirimleri (onaylı)"}
AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
TUR_ADI = {"yeni": "Yeni açılan", "guncellendi": "Güncellenen", "kapandi": "Kapanan"}


def _sayi(n):
    return f"{n:,}".replace(",", ".")


def _yuzde(a, b):
    return round(100 * a / b) if b else 0


def _cubuklar(satirlar, birim="tesis", baglanti=None):
    """Yatay çubuk grafik: [(etiket, değer)], tek seri, değer etiketi her satırda."""
    en_cok = max((v for _, v in satirlar), default=1) or 1
    toplam = sum(v for _, v in satirlar) or 1
    return '<div class="cubuklar">' + "".join(
        f"""<div class="cubuk" data-ipucu="{escape(e)}: {_sayi(v)} {birim} (%{_yuzde(v, toplam)})">
          <span class="cubuk-ad">{f'<a href="{baglanti(e)}">{escape(e)}</a>' if baglanti else escape(e)}</span>
          <span class="cubuk-iz"><i style="width:{max(1.5, v / en_cok * 100):.1f}%"></i></span>
          <span class="cubuk-deger">{_sayi(v)}</span></div>""" for e, v in satirlar) + "</div>"


def _durum_rozet(tur, metin):
    ikon = {"iyi": "✓", "uyari": "!", "kritik": "✕"}[tur]
    return f'<span class="durum durum-{tur}"><b aria-hidden="true">{ikon}</b>{escape(metin)}</span>'


def _kalite(etiket, n, toplam, aciklama):
    y = _yuzde(n, toplam)
    tur = "iyi" if y >= 90 else "uyari" if y >= 50 else "kritik"
    return f"""<div class="kalite">
      <div class="kalite-ust"><b>{etiket}</b>{_durum_rozet(tur, f"%{y}")}</div>
      <div class="olcer olcer-{tur}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{y}" aria-label="{escape(etiket)}"><i style="width:{y}%"></i></div>
      <p class="soluk">{_sayi(n)} / {_sayi(toplam)} tesis · {escape(aciklama)}</p></div>"""


def uret(cikti, anlik, gunluk, durum):
    simdi = datetime.now(timezone.utc)
    tesisler = [f["properties"] for f in anlik["features"]]
    n = len(tesisler)
    bakanliklar = Counter(p["bakanlik"] for p in tesisler)
    iller = Counter(p["il"] for p in tesisler if p["il"])
    son30 = [o for o in gunluk if datetime.fromisoformat(o["tarih"]) >= simdi - timedelta(days=30)]
    guncelleme = datetime.fromisoformat(anlik["guncelleme"])
    son_calisma = datetime.fromisoformat(durum["son_calisma"]) if durum.get("son_calisma") else None

    # Özet göstergeler
    tile = lambda deger, ad, alt="": f'<div class="gosterge"><b>{deger}</b><span>{ad}</span>{f"<small>{alt}</small>" if alt else ""}</div>'
    gostergeler = "".join([
        tile(_sayi(n), "kamu tesisi", f"{len(bakanliklar)} bakanlığa bağlı"),
        tile(f"{len(iller)}/81", "il kapsanıyor", "%" + str(_yuzde(len(iller), 81)) + " il kapsamı"),
        tile(_sayi(len(son30)), "değişiklik (30 gün)",
             " · ".join(f"{_sayi(sum(o['tur'] == t for o in son30))} {a.lower()}" for t, a in TUR_ADI.items())),
        tile(son_calisma.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m %H:%M") if son_calisma else "—",
             "son otomatik kontrol", "Günde 2 kez · 07:17 ve 19:17"),
    ])

    # Dağılımlar
    bakanlik_grafik = _cubuklar([(kisa(b), v) for b, v in bakanliklar.most_common()])
    il_sira = iller.most_common()
    il_grafik = _cubuklar(il_sira[:15], baglanti=lambda il: f"il/{slug(il)}.html")
    il_tablo = "".join(f"<tr><td><a href=\"il/{slug(il)}.html\">{escape(il)}</a></td><td>{v}</td></tr>"
                       for il, v in sorted(iller.items(), key=lambda x: anahtar_metin(x[0])))
    il_bakanlik = defaultdict(Counter)
    for p in tesisler:
        if p["il"]:
            il_bakanlik[p["il"]][kisa(p["bakanlik"])] += 1

    # Veri kalitesi
    kesin = sum(p["konumKaynagi"] == "adres" for p in tesisler)
    ilce = sum(p["konumKaynagi"] == "ilce" for p in tesisler)
    resmi = sum(".gov.tr" in p["kaynakUrl"] or "RESMİ" in p["kaynakUrl"].upper() for p in tesisler)
    kalite = "".join([
        _kalite("Telefon numarası", sum(gercek_tel(p["telefon"]) for p in tesisler), n, "aranabilir numara kayıtlı"),
        _kalite("Resmî kaynak", resmi, n, "bilgi bir .gov.tr sayfasına dayanıyor"),
        _kalite("Konum (ilçe veya daha iyi)", kesin + ilce, n, "haritada ilçe merkezi veya kesin adres"),
        _kalite("Açık adres", sum(bool(p["adres"]) for p in tesisler), n, "sokak/mahalle düzeyinde adres var"),
        _kalite("Kesin konum", kesin, n, "koordinat adresten bulundu"),
    ])

    # Kaynak durumu
    kaynak_satir = []
    sayac_kaynak = Counter(p["kaynakKodu"] for p in tesisler)
    for kod, kd in durum.get("kaynaklar", {}).items():
        sb = datetime.fromisoformat(kd["son_basari"]) if kd.get("son_basari") else None
        if kd.get("hata"):
            rozet = _durum_rozet("kritik", "Hata")
        elif sb and simdi - sb < timedelta(hours=26):
            rozet = _durum_rozet("iyi", "Çalışıyor")
        else:
            rozet = _durum_rozet("uyari", "Gecikmeli")
        kaynak_satir.append(f"""<tr><td>{escape(KAYNAK_ADI.get(kod, kod))}</td><td>{rozet}</td>
          <td>{sb.astimezone(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M') if sb else '—'}</td>
          <td class="sag">{_sayi(sayac_kaynak.get(kod, 0))}</td></tr>""")
    if sayac_kaynak.get("bildirim"):
        kaynak_satir.append(f"<tr><td>{KAYNAK_ADI['bildirim']}</td><td>{_durum_rozet('iyi', 'Aktif')}</td><td>—</td>"
                            f"<td class=\"sag\">{_sayi(sayac_kaynak['bildirim'])}</td></tr>")

    # Aylık değişiklik
    aylik = defaultdict(Counter)
    for o in gunluk:
        t = datetime.fromisoformat(o["tarih"])
        aylik[(t.year, t.month)][o["tur"]] += 1
    if aylik:
        en_cok = max(sum(c.values()) for c in aylik.values())
        aylar = sorted(aylik)[-12:]
        sutunlar = "".join(
            f"""<div class="sutun" data-ipucu="{AYLAR[a - 1]} {y}: {' · '.join(f"{aylik[(y, a)][t]} {TUR_ADI[t].lower()}" for t in TUR_ADI)}">
              <div class="yigin" style="height:{sum(aylik[(y, a)].values()) / en_cok * 100:.1f}%">
              {''.join(f'<i class="y-{t}" style="flex:{aylik[(y, a)][t]}"></i>' for t in ("kapandi", "guncellendi", "yeni") if aylik[(y, a)][t])}
              </div><span>{AYLAR[a - 1]}</span></div>""" for y, a in aylar)
        trend = f"""<div class="lejant">{''.join(f'<span><i class="y-{t}"></i>{a}</span>' for t, a in TUR_ADI.items())}</div>
          <div class="sutunlar">{sutunlar}</div>"""
    else:
        trend = ('<div class="bos-kart">Sistem ilk yüklemeden bu yana henüz bir değişiklik tespit etmedi. '
                 'Kaynaklarda yeni açılış, kapanış veya bilgi değişikliği olduğunda burada aylık olarak görünecek.</div>')

    # TUCBS uyum durumu
    tucbs = [
        ("iyi", "ISO 19115/19139 üst veri kaydı", "metadata.xml olarak yayında, her güncellemede yenilenir"),
        ("iyi", "Kalıcı nesne kimliği", "her tesisin değişmeyen bir kodu var (tesisId)"),
        ("iyi", "Açık veri formatları", "GeoJSON (EPSG:4326) ve CSV indirilebilir"),
        ("iyi", "Değişiklik kaydı ve izlenebilirlik", "her değişiklik tarih, eski ve yeni değerle saklanıyor; RSS ile yayınlanıyor"),
        ("uyari", "TUCBS tema şemasına tam eşleme", "planlandı (Kamu Hizmetleri / Yapı teması)"),
        ("uyari", "TUREF/TM koordinat çıktısı", "planlandı (EPSG:5254–5259)"),
        ("uyari", "OGC WMS/WFS/CSW servisleri", "planlandı, sunucu gerektirir"),
    ]
    tucbs_html = "".join(f"<li>{_durum_rozet(t, 'Tamam' if t == 'iyi' else 'Planlandı')}<div><b>{escape(a)}</b>"
                         f"<p class=\"soluk\">{escape(d)}</p></div></li>" for t, a, d in tucbs)

    rapor_tarihi = simdi.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M")
    govde = f"""
<div class="panel-arac">
  <p class="soluk">Rapor tarihi: {rapor_tarihi} · Son veri değişikliği: {guncelleme.strftime('%d.%m.%Y')}</p>
  <button class="dugme ana" type="button" onclick="window.print()">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/></svg>
    Raporu yazdır / PDF kaydet</button>
</div>
<div class="rapor-baslik"><h1>Kamu Misafirhaneleri – Yönetim Raporu</h1><p>{rapor_tarihi}</p></div>

<section class="gostergeler" aria-label="Özet göstergeler">{gostergeler}</section>

<div class="panel-izgara">
  <div class="yigin-sutun">
  <section class="kart"><h2>Bakanlıklara göre tesis sayısı</h2>{bakanlik_grafik}</section>
  <section class="kart"><h2>Veri kalitesi</h2><div class="kaliteler">{kalite}</div></section>
  </div>
  <div class="yigin-sutun">
  <section class="kart"><h2>En çok tesis bulunan 15 il</h2>{il_grafik}
    <details><summary>Tüm illeri tablo olarak göster</summary>
      <table class="tablo"><thead><tr><th>İl</th><th>Tesis</th></tr></thead><tbody>{il_tablo}</tbody></table></details>
  </section>
  <section class="kart"><h2>Veri kaynakları ve sistem durumu</h2>
    <table class="tablo"><thead><tr><th>Kaynak</th><th>Durum</th><th>Son başarılı okuma</th><th class="sag">Tesis</th></tr></thead>
    <tbody>{''.join(kaynak_satir)}</tbody></table>
    <p class="soluk not-alt">Sistem günde iki kez kaynakları kendiliğinden okur, değişiklikleri tespit eder ve yayınlar. Bir kaynak hata verirse
    o kaynağın önceki verisi korunur; hiçbir tesis yanlışlıkla "kapandı" olarak yayınlanmaz.</p>
  </section>
  </div>
  <section class="kart genis"><h2>Aylık değişiklikler</h2>{trend}</section>
  <section class="kart genis"><h2>TUCBS ve açık veri uyumu</h2><ul class="uyum">{tucbs_html}</ul></section>
</div>"""
    (cikti / "yonetim.html").write_text(iskelet(
        "Yönetim paneli | Kamu Misafirhaneleri",
        "Kamu misafirhaneleri veri setinin özet göstergeleri, veri kalitesi ve sistem durumu.",
        govde, aktif="Panel",
        hero="<h1>Yönetim paneli</h1><p>Tesis envanteri, veri kalitesi ve otomatik güncelleme sisteminin durumu – tek sayfada.</p>"))
