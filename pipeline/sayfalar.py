"""Tesis ve il sayfaları, site haritası ve uygulama (PWA) dosyaları."""
import json
import os
import re
from collections import defaultdict
from html import escape
from urllib.parse import quote, urlencode

from pipeline.model import anahtar_metin
from pipeline.notify import ETIKET

DEPO = os.environ.get("GITHUB_REPOSITORY", "bayramseyma091-coder/kamu-misafirhaneleri")
SURUM_YER = "{{SURUM}}"  # site.py tarafından CSS/JS sürümüyle değiştirilir

LEAFLET = """<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">"""
LEAFLET_JS = """<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>"""
LOGO = ('<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="rgba(255,255,255,.16)"/>'
        '<path d="M8 23V14l8-6 8 6v9h-5v-5h-6v5z" fill="#fff"/></svg>')
TEL_IKON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 '
            '19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 '
            '0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>')
RENKLER = {
    "Millî Eğitim Bakanlığı": "#2563eb",
    "İçişleri Bakanlığı": "#dc2626",
    "Millî Savunma Bakanlığı": "#4d7c0f",
    "Kültür ve Turizm Bakanlığı": "#9333ea",
    "Sağlık Bakanlığı": "#0891b2",
}


def renk(bakanlik):
    return RENKLER.get(bakanlik, "#64748b")


def kisa(bakanlik):
    return re.sub(r" Bakanlığı$", "", bakanlik)


def slug(*parcalar):
    return re.sub(r"\s+", "-", anahtar_metin(" ".join(p for p in parcalar if p)))[:90].strip("-")


def tel_link(t):
    return "tel:" + re.sub(r"[^\d+]", "", re.split(r"[/(]", t)[0])


def gercek_tel(t):
    return len(re.sub(r"\D", "", t or "")) >= 7


def tel_yaz(t):
    if not t:
        return ""
    if gercek_tel(t):
        return f'<a class="tel" href="{tel_link(t)}">{TEL_IKON}{escape(t)}</a>'
    return f'<span class="tel-yok">{escape(t.strip("()"))}</span>'


def kaynak_url(metin):
    m = re.search(r"https?://\S+", metin or "")
    return m.group(0).rstrip(").,") if m else ""


def iskelet(baslik, aciklama, govde, kok="", aktif="", hero="", ek_bas="", ek_son="", jsonld=None):
    nav = "".join(
        f'<a href="{kok}{h}"{" aria-current=\"page\"" if aktif == a else ""}>{a}</a>'
        for a, h in (("Harita", "./"), ("İller", "iller.html"), ("Değişiklikler", "degisiklikler.html"), ("Panel", "yonetim.html"),
                     ("RSS", "rss.xml")))
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(baslik)}</title>
<meta name="description" content="{escape(aciklama)}">
<meta property="og:title" content="{escape(baslik)}">
<meta property="og:description" content="{escape(aciklama)}">
<meta name="theme-color" content="#0b2a45">
<link rel="icon" href="{kok}simge.svg" type="image/svg+xml">
<link rel="manifest" href="{kok}manifest.webmanifest">
<link rel="apple-touch-icon" href="{kok}simge-192.png">
<link rel="alternate" type="application/rss+xml" title="Değişiklikler" href="{kok}rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
{ek_bas}
<link rel="stylesheet" href="{kok}stil.css">
{ld}
</head>
<body>
<header class="ust">
  <div class="kap menu">
    <a class="logo" href="{kok}./">{LOGO}Kamu Misafirhaneleri</a>
    <nav>{nav}</nav>
  </div>
  <div class="kap hero hero-kucuk">{hero}</div>
</header>
<main class="kap bolum">
{govde}
</main>
<footer class="alt-bilgi"><div class="kap"><div>
  <p>Bilgiler resmî kurum sitelerinden otomatik derlenir ve hata içerebilir. Rezervasyondan önce tesisi arayarak teyit edin.</p>
  <p>Harita © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıcıları.</p>
</div><div><ul>
  <li><a href="{kok}misafirhaneler.geojson">GeoJSON</a> · <a href="{kok}misafirhaneler.csv">CSV</a> · <a href="{kok}metadata.xml">ISO 19139</a></li>
</ul></div></div></footer>
{ek_son}
<script>if("serviceWorker" in navigator)navigator.serviceWorker.register("{kok}sw.js");</script>
</body>
</html>
"""


def bildir_url(p=None):
    """Önceden doldurulmuş GitHub bildirim formu bağlantısı."""
    alanlar = {"template": "bilgi-bildir.yml"}
    if p:
        alanlar.update(title=f"[Bildirim] {p['tesisAdi']} ({p['il']})", tesis_id=p["tesisId"],
                       tesis_adi=p["tesisAdi"], il=p["il"], ilce=p["ilce"], adres=p["adres"], telefon=p["telefon"])
    else:
        alanlar.update(title="[Yeni tesis] ", tur="Yeni tesis öneriyorum")
    return f"https://github.com/{DEPO}/issues/new?" + urlencode(alanlar, quote_via=quote)


def _tesis_sayfasi(f, olaylar, il_slug, site_url):
    p = f["properties"]
    g = f.get("geometry")
    yer = f'{p["il"]}{" / " + p["ilce"] if p["ilce"] else ""}'
    sorgu = quote(f'{p["tesisAdi"]} {p["ilce"]} {p["il"]}')
    kaynak = kaynak_url(p["kaynakUrl"])
    satir = lambda baslik, deger: f"<div><dt>{baslik}</dt><dd>{deger}</dd></div>" if deger else ""
    gecmis = "".join(
        f"""<article class="olay olay-{o['tur']}"><div class="olay-ust"><span class="rozet">{ETIKET[o['tur']]}</span>
        <time datetime="{o['tarih']}">{o['tarih'][:10]}</time></div>
        {''.join(f'<p><b>{escape(a)}</b>: <del>{escape(e or "—")}</del> → <ins>{escape(y or "—")}</ins></p>' for a, (e, y) in o.get('farklar', {}).items())}
        </article>""" for o in olaylar)
    harita = ""
    if g:
        x, y = g["coordinates"]
        yaklasik = p["konumKaynagi"] != "adres"
        harita = f"""<div class="kart mini-harita-kap"><div id="mini-harita" data-x="{x}" data-y="{y}" data-renk="{renk(p['bakanlik'])}"></div>
        {'<p class="not">Konum yaklaşık (' + ('il' if p['konumKaynagi'] == 'il' else 'ilçe') + ' merkezi). Yol tarifi için butonları kullanın.</p>' if yaklasik else ''}</div>"""
    govde = f"""
<nav class="iz" aria-label="Konum"><a href="../">Ana sayfa</a> › <a href="../il/{il_slug}.html">{escape(p['il'] or 'Diğer')}</a> › <span>{escape(p['tesisAdi'])}</span></nav>
<div class="detay">
  <div>
    <div class="kart">
      <span class="bakanlik-rozet" style="--renk:{renk(p['bakanlik'])}"><i></i>{escape(p['bakanlik'])}</span>
      <dl class="bilgi">
        {satir("Konum", escape(yer))}
        {satir("Adres", escape(p['adres']))}
        {satir("Telefon", tel_yaz(p['telefon']))}
        {satir("Bağlı birim", escape(p['birim']))}
        {satir("Not", escape(p['not']))}
      </dl>
      <div class="eylemler">
        {f'<a class="dugme ana" href="{tel_link(p["telefon"])}">{TEL_IKON}Ara</a>' if gercek_tel(p['telefon']) else ''}
        <a class="dugme" href="https://www.google.com/maps/search/?api=1&query={sorgu}" target="_blank" rel="noopener">Google Haritalar'da yol tarifi</a>
        <a class="dugme" href="https://yandex.com.tr/harita/?text={sorgu}" target="_blank" rel="noopener">Yandex'te aç</a>
        <button class="dugme" type="button" data-paylas>Paylaş</button>
      </div>
    </div>
    <div class="kart">
      <h2>Bilginin kaynağı</h2>
      <p>{f'<a href="{escape(kaynak)}" target="_blank" rel="noopener">{escape(kaynak)}</a>' if kaynak else escape(p['kaynakUrl'] or '—')}</p>
      {f'<p class="soluk">{escape(p["dogrulama"])}</p>' if p['dogrulama'] else ''}
      <p class="bildir">Bilgiler yanlış ya da tesis kapanmış mı? <a href="{escape(bildir_url(p))}" target="_blank" rel="noopener">Hatalı bilgi bildirin →</a></p>
    </div>
    <div class="kart">
      <h2>Değişiklik geçmişi</h2>
      {f'<div class="zaman">{gecmis}</div>' if gecmis else '<p class="soluk">Sistem bu tesis için henüz bir değişiklik kaydetmedi.</p>'}
    </div>
  </div>
  <div>{harita}</div>
</div>"""
    jsonld = {"@context": "https://schema.org", "@type": "LodgingBusiness", "name": p["tesisAdi"],
              "telephone": p["telefon"] or None,
              "address": {"@type": "PostalAddress", "streetAddress": p["adres"] or None,
                          "addressLocality": p["ilce"] or None, "addressRegion": p["il"] or None, "addressCountry": "TR"},
              "parentOrganization": {"@type": "GovernmentOrganization", "name": p["bakanlik"]}}
    if g and p["konumKaynagi"] == "adres":
        jsonld["geo"] = {"@type": "GeoCoordinates", "longitude": g["coordinates"][0], "latitude": g["coordinates"][1]}
    return iskelet(
        f'{p["tesisAdi"]} – {yer} | Kamu Misafirhaneleri',
        f'{p["tesisAdi"]} ({yer}) iletişim bilgileri, telefon, adres ve yol tarifi. {p["bakanlik"]}.',
        govde, kok="../",
        hero=f'<h1>{escape(p["tesisAdi"])}</h1><p>{escape(yer)}</p>',
        ek_bas=LEAFLET, ek_son=LEAFLET_JS + '\n<script src="../sayfa.js"></script>', jsonld=jsonld)


def _il_sayfasi(il, tesisler):
    ilceler = defaultdict(list)
    for f in tesisler:
        ilceler[f["properties"]["ilce"] or "Merkez / belirtilmemiş"].append(f)
    sayac = defaultdict(int)
    for f in tesisler:
        sayac[f["properties"]["bakanlik"]] += 1
    ozet = " ".join(f'<span class="bakanlik-rozet" style="--renk:{renk(b)}"><i></i>{escape(kisa(b))} {n}</span>'
                    for b, n in sorted(sayac.items(), key=lambda x: -x[1]))
    bolumler = []
    for ilce in sorted(ilceler, key=lambda s: anahtar_metin(s)):
        kartlar = "".join(
            f"""<a class="tesis" href="../tesis/{f['sayfa']}.html" style="--renk:{renk(f['properties']['bakanlik'])}">
            <h3>{escape(f['properties']['tesisAdi'])}</h3>
            <div class="alt"><span class="etiket">{escape(kisa(f['properties']['bakanlik']))}</span>
            {f'<span class="tel">{TEL_IKON}{escape(f["properties"]["telefon"])}</span>' if gercek_tel(f['properties']['telefon']) else tel_yaz(f['properties']['telefon'])}</div></a>"""
            for f in ilceler[ilce])
        bolumler.append(f'<section class="kart ilce"><h2>{escape(ilce)} <span class="soluk">{len(ilceler[ilce])}</span></h2>{kartlar}</section>')
    noktalar = [[f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0], renk(f["properties"]["bakanlik"]),
                 f["properties"]["tesisAdi"], f["sayfa"]] for f in tesisler if f.get("geometry")]
    govde = f"""
<nav class="iz" aria-label="Konum"><a href="../">Ana sayfa</a> › <a href="../iller.html">İller</a> › <span>{escape(il)}</span></nav>
<div class="ozet-satir">{ozet}</div>
<div class="detay">
  <div class="ilce-liste">{''.join(bolumler)}</div>
  <div><div class="kart mini-harita-kap"><div id="mini-harita" data-noktalar="{escape(json.dumps(noktalar, ensure_ascii=False))}"></div></div></div>
</div>"""
    return iskelet(
        f"{il} kamu misafirhaneleri ve öğretmenevleri | Kamu Misafirhaneleri",
        f"{il} ilindeki {len(tesisler)} kamu misafirhanesi, öğretmenevi ve sosyal tesisin telefon, adres ve harita bilgileri.",
        govde, kok="../", aktif="İller",
        hero=f"<h1>{escape(il)} kamu misafirhaneleri</h1><p>{len(tesisler)} tesis · {len(ilceler)} ilçe</p>",
        ek_bas=LEAFLET, ek_son=LEAFLET_JS + '\n<script src="../sayfa.js"></script>')


def _iller_sayfasi(iller):
    en_cok = max(len(v) for v in iller.values())
    kartlar = "".join(
        f"""<a class="il-kart" href="il/{s}.html" data-ad="{escape(anahtar_metin(il))}">
        <b>{escape(il)}</b><span>{len(t)} tesis</span><i style="width:{max(4, round(len(t) / en_cok * 100))}%"></i></a>"""
        for il, (s, t) in sorted(((il, (slug(il) or "diger", t)) for il, t in iller.items()), key=lambda x: anahtar_metin(x[0])))
    govde = f"""<div class="panel panel-duz"><div class="arama"><label>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="il-ara" type="search" placeholder="İl ara…" aria-label="İl ara" autocomplete="off"></label></div></div>
<div class="il-izgara" id="il-izgara">{kartlar}</div>"""
    return iskelet(
        "İllere göre kamu misafirhaneleri | Kamu Misafirhaneleri",
        "Türkiye'nin 81 ilindeki kamu misafirhaneleri ve öğretmenevleri, il il liste.",
        govde, aktif="İller",
        hero=f"<h1>İllere göre misafirhaneler</h1><p>{len(iller)} il · {sum(len(t) for t in iller.values())} tesis</p>",
        ek_son='<script src="sayfa.js"></script>')


def uret(cikti, anlik, gunluk, site_url):
    """Sayfaları üretir; her tesise 'sayfa' (dosya adı) atar ve onu döndürür."""
    olay_tesis = defaultdict(list)
    for o in gunluk:
        olay_tesis[o["tesis"]["tesisId"]].append(o)

    kullanilan = set()
    iller = defaultdict(list)
    for f in anlik["features"]:
        p = f["properties"]
        s = slug(p["tesisAdi"], p["ilce"], p["il"]) or p["tesisId"].lower()
        if s in kullanilan:
            s = f'{s}-{p["tesisId"][3:9].lower()}'
        kullanilan.add(s)
        f["sayfa"] = s
        iller[p["il"] or "Diğer"].append(f)

    (cikti / "tesis").mkdir()
    (cikti / "il").mkdir()
    for il, tesisler in iller.items():
        il_slug = slug(il) or "diger"
        (cikti / "il" / f"{il_slug}.html").write_text(_il_sayfasi(il, tesisler))
        for f in tesisler:
            (cikti / "tesis" / f"{f['sayfa']}.html").write_text(
                _tesis_sayfasi(f, olay_tesis.get(f["properties"]["tesisId"], []), il_slug, site_url))
    (cikti / "iller.html").write_text(_iller_sayfasi(iller))

    # Arama motorları için site haritası
    adresler = ["", "iller.html", "degisiklikler.html", "yonetim.html"] + [f"il/{slug(il) or 'diger'}.html" for il in iller] + \
               [f"tesis/{f['sayfa']}.html" for f in anlik["features"]]
    tarih = anlik["guncelleme"][:10]
    (cikti / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"<url><loc>{site_url}{a}</loc><lastmod>{tarih}</lastmod></url>\n" for a in adresler) + "</urlset>\n")
    (cikti / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}sitemap.xml\n")
    return {f["properties"]["tesisId"]: f["sayfa"] for f in anlik["features"]}
