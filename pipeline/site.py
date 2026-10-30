"""Statik siteyi _site/ klasörüne üretir (GitHub Pages bu klasörü yayınlar)."""
import json
import os
import shutil
from datetime import datetime
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from pipeline.notify import ETIKET, metin

KOK = Path(__file__).resolve().parents[1]
VERI = KOK / "data"
SABLON = KOK / "site"
CIKTI = KOK / "_site"
RSS_KAYIT = 100


def _site_url():
    return os.environ.get("SITE_URL", "")


def _tarih(iso):
    return datetime.fromisoformat(iso)


def _rss(gunluk, guncelleme):
    url = _site_url()
    ogeler = []
    for o in gunluk[:RSS_KAYIT]:
        t = o["tesis"]
        baslik = f'{ETIKET[o["tur"]]}: {t["tesisAdi"]} ({t["il"]})'
        ogeler.append(f"""  <item>
    <title>{xml_escape(baslik)}</title>
    <link>{url}degisiklikler.html#{t["tesisId"]}</link>
    <guid isPermaLink="false">{t["tesisId"]}-{o["tur"]}-{o["tarih"]}</guid>
    <pubDate>{format_datetime(_tarih(o["tarih"]))}</pubDate>
    <category>{o["tur"]}</category>
    <description>{xml_escape(metin(o)).replace(chr(10), "&lt;br/&gt;")}</description>
  </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Kamu Misafirhaneleri – Değişiklikler</title>
  <link>{url}</link>
  <description>Yeni açılan, güncellenen ve kapanan kamu misafirhaneleri</description>
  <language>tr</language>
  <lastBuildDate>{format_datetime(_tarih(guncelleme))}</lastBuildDate>
{chr(10).join(ogeler)}
</channel>
</rss>
"""


def _degisiklik_sayfasi(gunluk):
    satirlar = []
    for o in gunluk[:1000]:
        t = o["tesis"]
        farklar = "".join(
            f'<li><b>{escape(a)}</b>: <del>{escape(e or "—")}</del> → <ins>{escape(y or "—")}</ins></li>'
            for a, (e, y) in o.get("farklar", {}).items())
        satirlar.append(f"""<article class="olay olay-{o['tur']}" id="{t['tesisId']}">
  <div class="olay-ust"><span class="rozet rozet-{o['tur']}">{ETIKET[o['tur']]}</span>
  <time datetime="{o['tarih']}">{_tarih(o['tarih']).strftime('%d.%m.%Y %H:%M')} UTC</time></div>
  <h3>{escape(t['tesisAdi'])}</h3>
  <p class="soluk">{escape(t['il'])}{' / ' + escape(t['ilce']) if t['ilce'] else ''} · {escape(t['bakanlik'])}</p>
  {f'<ul class="farklar">{farklar}</ul>' if farklar else ''}
</article>""")
    govde = "\n".join(satirlar) or '<p class="soluk">Henüz kayıtlı değişiklik yok. İlk veri yüklemesinden sonraki değişiklikler burada listelenecek.</p>'
    sablon = (SABLON / "degisiklikler.html").read_text()
    return sablon.replace("{{OLAYLAR}}", govde)


def _metaveri(anlik, guncelleme):
    """ISO 19115/19139 temel üst veri kaydı (CSW kataloğuna aktarılabilir)."""
    xs = [f["geometry"]["coordinates"] for f in anlik["features"] if f.get("geometry")]
    bati, dogu = (min(x for x, _ in xs), max(x for x, _ in xs)) if xs else (26.0, 45.0)
    guney, kuzey = (min(y for _, y in xs), max(y for _, y in xs)) if xs else (36.0, 42.1)
    url = _site_url()
    gs = lambda s: f"<gco:CharacterString>{xml_escape(s)}</gco:CharacterString>"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:fileIdentifier>{gs("kamu-misafirhaneleri")}</gmd:fileIdentifier>
  <gmd:language><gmd:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/" codeListValue="tur">tur</gmd:LanguageCode></gmd:language>
  <gmd:hierarchyLevel><gmd:MD_ScopeCode codeList="http://standards.iso.org/iso/19139/resources/gmxCodelists.xml#MD_ScopeCode" codeListValue="dataset">dataset</gmd:MD_ScopeCode></gmd:hierarchyLevel>
  <gmd:dateStamp><gco:DateTime>{guncelleme}</gco:DateTime></gmd:dateStamp>
  <gmd:metadataStandardName>{gs("ISO 19115:2003/19139")}</gmd:metadataStandardName>
  <gmd:referenceSystemInfo><gmd:MD_ReferenceSystem><gmd:referenceSystemIdentifier><gmd:RS_Identifier>
    <gmd:code>{gs("EPSG:4326")}</gmd:code></gmd:RS_Identifier></gmd:referenceSystemIdentifier></gmd:MD_ReferenceSystem></gmd:referenceSystemInfo>
  <gmd:identificationInfo><gmd:MD_DataIdentification>
    <gmd:citation><gmd:CI_Citation>
      <gmd:title>{gs("Kamu Misafirhaneleri")}</gmd:title>
      <gmd:date><gmd:CI_Date><gmd:date><gco:DateTime>{guncelleme}</gco:DateTime></gmd:date>
        <gmd:dateType><gmd:CI_DateTypeCode codeList="http://standards.iso.org/iso/19139/resources/gmxCodelists.xml#CI_DateTypeCode" codeListValue="revision">revision</gmd:CI_DateTypeCode></gmd:dateType></gmd:CI_Date></gmd:date>
    </gmd:CI_Citation></gmd:citation>
    <gmd:abstract>{gs(f"Türkiye'deki kamu kurumlarına ait misafirhane, öğretmenevi ve sosyal tesislerin konum ve iletişim bilgileri. Resmî kaynaklardan otomatik derlenir. Kayıt sayısı: {len(anlik['features'])}.")}</gmd:abstract>
    <gmd:resourceMaintenance><gmd:MD_MaintenanceInformation><gmd:maintenanceAndUpdateFrequency>
      <gmd:MD_MaintenanceFrequencyCode codeList="http://standards.iso.org/iso/19139/resources/gmxCodelists.xml#MD_MaintenanceFrequencyCode" codeListValue="daily">daily</gmd:MD_MaintenanceFrequencyCode>
    </gmd:maintenanceAndUpdateFrequency></gmd:MD_MaintenanceInformation></gmd:resourceMaintenance>
    <gmd:language><gmd:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/" codeListValue="tur">tur</gmd:LanguageCode></gmd:language>
    <gmd:topicCategory><gmd:MD_TopicCategoryCode>structure</gmd:MD_TopicCategoryCode></gmd:topicCategory>
    <gmd:extent><gmd:EX_Extent><gmd:geographicElement><gmd:EX_GeographicBoundingBox>
      <gmd:westBoundLongitude><gco:Decimal>{bati}</gco:Decimal></gmd:westBoundLongitude>
      <gmd:eastBoundLongitude><gco:Decimal>{dogu}</gco:Decimal></gmd:eastBoundLongitude>
      <gmd:southBoundLatitude><gco:Decimal>{guney}</gco:Decimal></gmd:southBoundLatitude>
      <gmd:northBoundLatitude><gco:Decimal>{kuzey}</gco:Decimal></gmd:northBoundLatitude>
    </gmd:EX_GeographicBoundingBox></gmd:geographicElement></gmd:EX_Extent></gmd:extent>
  </gmd:MD_DataIdentification></gmd:identificationInfo>
  <gmd:distributionInfo><gmd:MD_Distribution><gmd:transferOptions><gmd:MD_DigitalTransferOptions>
    <gmd:onLine><gmd:CI_OnlineResource><gmd:linkage><gmd:URL>{url}misafirhaneler.geojson</gmd:URL></gmd:linkage>
      <gmd:protocol>{gs("WWW:DOWNLOAD-1.0-http--download")}</gmd:protocol><gmd:name>{gs("GeoJSON")}</gmd:name></gmd:CI_OnlineResource></gmd:onLine>
    <gmd:onLine><gmd:CI_OnlineResource><gmd:linkage><gmd:URL>{url}misafirhaneler.csv</gmd:URL></gmd:linkage>
      <gmd:protocol>{gs("WWW:DOWNLOAD-1.0-http--download")}</gmd:protocol><gmd:name>{gs("CSV")}</gmd:name></gmd:CI_OnlineResource></gmd:onLine>
  </gmd:MD_DigitalTransferOptions></gmd:transferOptions></gmd:MD_Distribution></gmd:distributionInfo>
</gmd:MD_Metadata>
"""


def uret():
    anlik = json.loads((VERI / "misafirhaneler.geojson").read_text())
    gunluk = json.loads((VERI / "degisiklikler.json").read_text())
    guncelleme = anlik["guncelleme"]
    if CIKTI.exists():
        shutil.rmtree(CIKTI)
    shutil.copytree(SABLON, CIKTI, ignore=shutil.ignore_patterns("degisiklikler.html"))
    for ad in ("misafirhaneler.geojson", "misafirhaneler.csv", "degisiklikler.json"):
        shutil.copy(VERI / ad, CIKTI / ad)
    (CIKTI / "degisiklikler.html").write_text(_degisiklik_sayfasi(gunluk))
    (CIKTI / "rss.xml").write_text(_rss(gunluk, guncelleme))
    (CIKTI / "metadata.xml").write_text(_metaveri(anlik, guncelleme))
    (CIKTI / ".nojekyll").write_text("")
