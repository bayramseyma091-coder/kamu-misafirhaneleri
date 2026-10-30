# Kamu Misafirhaneleri

Türkiye'deki kamu misafirhanelerini, öğretmenevlerini ve sosyal tesisleri toplayan, kendi kendini güncelleyen bir web sitesi.
Yeni açılan, bilgisi değişen veya kapanan bir tesis olduğunda bunu sitede, RSS akışında ve (isteğe bağlı) Telegram kanalında otomatik yayınlar.

## Nasıl çalışır

Günde iki kez (07:17 ve 19:17 TSİ) GitHub Actions şu adımları çalıştırır:

1. **Topla:** `pipeline/sources/` altındaki kaynaklar okunur.
   - `manuel`: `data/kaynak/kamu_misafirhaneleri.xlsx` (elle tutulan liste)
   - `meb_dhgm`: MEB DHGM resmî öğretmenevi listesi (çalıştığında Excel'deki öğretmenevi satırlarının yerine geçer)
2. **Konumla:** Adresler OpenStreetMap Nominatim ile koordinata çevrilir. Adres bulunamazsa ilçe, o da yoksa il merkezi kullanılır. Sonuçlar `data/konum_onbellek.json` dosyasında saklanır.
3. **Karşılaştır:** Yeni veri bir önceki `data/misafirhaneler.geojson` ile karşılaştırılır. Değişiklikler `data/degisiklikler.json` dosyasına yazılır.
4. **Yayınla:** `_site/` klasörü üretilir ve GitHub Pages'e gönderilir. Değişiklik varsa Telegram bildirimi atılır.

### Güvenlik önlemleri

- Bir kaynak hata verirse o kaynağın önceki kayıtları korunur. Hiçbir tesis yanlışlıkla "kapandı" olarak yayınlanmaz.
- Bir kaynaktan önceki kayıtların yarısından azı gelirse kapanışlar yok sayılır.
- Yeni bir kaynak ilk kez çalıştığında mevcut verinin yerine sessizce geçer, bildirim yağmuru olmaz.

## Elle güncelleme

Excel dosyasını düzenleyip `data/kaynak/` altına aynı adla koyun ve depoya gönderin (GitHub web arayüzünden "Upload files" yeterli).
Sistem birkaç dakika içinde değişiklikleri tespit edip yayınlar.

## Kurulum (bir kerelik)

1. **Pages:** Depo → Settings → Pages → Source: **GitHub Actions**
2. **Telegram (isteğe bağlı):** @BotFather ile bot oluşturun, botu kanalınıza yönetici olarak ekleyin. Sonra Settings → Secrets and variables → Actions altına şunları ekleyin:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID` (örn. `@kanaladi`)
3. **İlk çalıştırma:** Actions → "Verileri güncelle ve yayınla" → **Run workflow**

## Çıktılar

| Dosya | İçerik |
|---|---|
| `index.html` | Harita ve aranabilir liste |
| `degisiklikler.html` | Değişiklik geçmişi |
| `rss.xml` | Son 100 değişiklik (RSS 2.0) |
| `misafirhaneler.geojson` | Tüm tesisler, EPSG:4326 |
| `misafirhaneler.csv` | Aynı veri, Excel'de açılabilir |
| `metadata.xml` | ISO 19115/19139 üst veri kaydı |

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
python -m pipeline.run --bildirimsiz      # --konumsuz: koordinat sorgulamasını atla
python -m http.server -d _site 8000
```

## TUCBS uyumu – durum

- [x] ISO 19115/19139 üst veri
- [x] Kalıcı nesne kimliği (`tesisId`), coğrafi veri GeoJSON / EPSG:4326
- [ ] TUCBS tema şemasına (Kamu Hizmetleri / Yapı) tam alan eşlemesi
- [ ] TUREF/TM (EPSG:5254–5259) çıktısı
- [ ] GeoServer ile WMS/WFS, GeoNetwork ile CSW servisleri (sunucu gerektirir)

## Yeni kaynak ekleme

`pipeline/sources/` altına `KOD` sabiti ve kayıt listesi döndüren bir `topla()` fonksiyonu içeren bir modül ekleyin. Kayıtlar `pipeline.model.kayit()` ile oluşturulur. Ardından modülü `pipeline/run.py` içindeki `KAYNAKLAR` listesine ekleyin.
