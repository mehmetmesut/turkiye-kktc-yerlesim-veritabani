# Türkiye ve KKTC Yerleşim Veritabanı · Türkiye & Northern Cyprus Gazetteer

[🇹🇷 Türkçe](#-türkçe) · [🇬🇧 English](#-english)

Türkiye ve Kuzey Kıbrıs Türk Cumhuriyeti'nin il, ilçe, semt, mahalle, köy, bağlı birim, posta kodu ve plaka kodu bilgilerini tek bir veri setinde toplayan, resmî kaynaklardan derlenmiş açık veritabanı.

A single, open dataset of provinces, districts, quarters, neighbourhoods, villages, hamlets, postal codes and licence-plate codes for Türkiye and the Turkish Republic of Northern Cyprus, compiled from official sources.

| | Türkiye | KKTC | Toplam |
|---|---:|---:|---:|
| İl / Province | 81 | 6 | 87 |
| İlçe / District (KKTC: bucak) | 973 | 29 | 1.002 |
| Mahalle / Neighbourhood | 34.563 | 98 | 34.661 |
| Köy / Village | 18.245 | 173 | 18.418 |
| Köy mahallesi / Village quarter | 18.165 | – | 18.165 |
| Bağlı birim / Hamlet | 23.552 | – | 23.552 |
| **Toplam / Total** | **94.525** | **271** | **94.796** |

- Posta kodu / Postal code: **%100 dolu / filled**. Türkiye'deki her kod, 14.11.2026'da PTT'den canlı alınan veride kendi ilçesinde geçerli bir koddur. Every Türkiye code is a valid code of its district in live PTT data retrieved on 14 Nov 2026.
- PTT'de karşılığı bulunamayan 541 kayıtta (%0,6) kod, aynı belde / ilçedeki en yaygın koddur ve `kaynak` alanında `tahmini-ilce` olarak işaretlidir. For 541 records (0.6%) with no PTT counterpart, the code is the most common code of the same town / district, flagged `tahmini-ilce` (estimated).
- Mükerrer yok / No duplicates: aynı il + ilçe + ad taşıyan satırlar ancak farklı yerlerdir (farklı belde, farklı köy ya da farklı tür). Rows sharing province + district + name are distinct places (different town, village or type).
- Semt dolu / With quarter: **%92,2** · Güncelleme / Updated: **14.11.2026**

---

## 🇹🇷 Türkçe

### İçerik

| Dosya | Açıklama |
|---|---|
| `veri/turkiye-kktc-yerlesim.json` | Tüm kayıtlar ve üst bilgi (`_meta`: kaynaklar, alan açıklamaları, sayılar) |
| `veri/turkiye-kktc-yerlesim.csv` | Aynı veri, CSV (UTF-8, virgül ayraçlı) |
| `veri/turkiye-kktc-yerlesim.xlsx` | Aynı veri, Excel (kodlar metin; baştaki sıfırlar korunur; süzgeçli) |
| `veri/turkiye-kktc-yerlesim.sql` | MySQL / MariaDB: `iller` → `ilceler` → `yerlesimler` ilişkili tablolar (utf8mb4_turkish_ci) |
| `veri/posta-kodlari/<il>.json` | İl başına hafif dosya: `{ "ilceler": { "<ilçe>": { "<mahalle / köy>": "<posta kodu>" } } }` — web formlarında posta kodu otomatik doldurmak için |
| `veri/eslesme-raporu.txt` | Kaynaklar arası eşleşme özeti ve eşleşmeyen kayıtlar |
| `araclar/` | Veriyi yeniden üreten betikler |

### Alanlar

| Alan | Açıklama |
|---|---|
| `id` | Sıra numarası |
| `ulke` | `TR` veya `KKTC` |
| `plaka` | İl plaka kodu (`"07"`); KKTC'de yok |
| `il` | İl. KKTC'de birinci düzey idari birim olan ilçe (Lefkoşa, Gazimağusa, Girne, Güzelyurt, İskele, Lefke) |
| `ilce` | İlçe. KKTC'de bucak |
| `semt` | PTT'nin semt / bucak / belde adı |
| `belde` | İçişleri kaydına göre mahallenin bağlı olduğu belde |
| `tur` | `mahalle`, `köy`, `köy mahallesi` (PTT: köyün içindeki mahalle) veya `bağlı` (İçişleri: köye bağlı mezra, mevki) |
| `ad` | Birimin adı |
| `koy` | Köy mahallesi ve bağlı birimlerde bağlı olduğu köy |
| `posta_kodu` | Birimde en çok kullanılan posta kodu (5 hane, metin) |
| `diger_posta_kodlari` | Birimin sokaklarında geçen diğer posta kodları |
| `eski_ad` | KKTC yerleşimlerinin eski adı |
| `kaynak` | Kaydı besleyen kaynaklar |

### Kaynaklar

| Kaynak | Kullanım |
|---|---|
| T.C. İçişleri Bakanlığı — [Mülki İdare Bölümleri Envanteri](https://www.e-icisleri.gov.tr/Anasayfa/MulkiIdariBolumleri.aspx) | Resmî mahalle, köy ve bağlı birim listesi (ana iskelet) |
| PTT — [Posta Kodu Sorgulama](https://www.ptt.gov.tr/posta-kodu) | Güncel posta kodları (sokak düzeyinden derlenmiş) |
| KKTC Posta Dairesi — [Posta Kodları](http://posta.gov.ct.tr/KURUMSAL/Posta-Kodlar%C4%B1) | KKTC ilçe, bucak, mahalle, köy ve posta kodları |
| PTT posta kodu listesi (12.05.2021) | Türkiye semt / bucak / belde adları; güncel listede bulunamayan kayıtlar için yedek posta kodu |
| Vikipedi — KKTC'deki yerleşim yerleri listesi | KKTC yerleşimlerinin eski adları |

Öncelik sırası: İçişleri (birim adı ve bağlılık) → PTT güncel (posta kodu) → eski PTT listeleri (semt ve yedek posta kodu). Adlar Türkçe yazım kurallarına göre büyük-küçük harfe çevrilmiştir.

`kaynak` değerleri: `icisleri` · `ptt` (güncel PTT, aynı ad) · `ptt-benzer-ad` / `ptt-benzer-ad-zayif` (aynı ilçede yazım farkı: 4 Eylül ↔ Dörteylül, Altınlı ↔ Altunlu) · `ptt-2021` / `ptt-2024` (eski PTT listesi) · `ptt-2021-semt` / `ptt-2021-belde` · türetilen kodlar: `koyden` (bağlı birim → köyü), `koy-mahallelerinden` (köy → köy mahalleleri), `beldeden`, `semtten`, `ilceden` (ilçedeki tüm köylerin ortak kodu) · `tahmini-ilce` (tahmini) · `kktc-posta`. Eşleştirme kararları `veri/eslesme-raporu.txt` dosyasında tek tek listelenir; `araclar/denetle.py` tüm denetimleri yeniden çalıştırır.
### Yeniden üretme

1. `python araclar/icisleri_indir.py <dizin>` — İçişleri Excel listelerini indirir (LibreOffice ile CSV'ye çevirin).
2. `araclar/ptt_tara.js` — PTT sorgu sayfasında tarayıcı konsolunda çalıştırılır; `ptt-guncel.json` üretir (sunucu hız sınırı nedeniyle ~1 saat).
3. `python araclar/yerlesim_birlestir.py <kaynak_dizini> veri <tarih>` — kaynakları birleştirir.

### Sınırlamalar

- Posta kodları PTT'nin yayımladığı veriye dayanır; bir mahallede birden çok posta kodu olabilir (`diger_posta_kodlari`).
- Semt bilgisi PTT'nin 2021 listesinden eşleştirilmiştir; sonradan açılan birimlerde boş olabilir.
- KKTC listesi Posta Dairesi'nin 13.05.2019 tarihli belgesidir.
- Veri bilgilendirme amaçlıdır; resmî işlemlerde ilgili kurumun güncel kaydı esas alınmalıdır.

### Destek

Bu çalışma işinize yaradıysa depoya ⭐ **yıldız** vererek ve [Tartışmalar](../../discussions) bölümüne kısa bir **teşekkür yorumu** yazarak destek olabilirsiniz. Hata ve güncelleme bildirimleri için [konu (issue)](../../issues) açabilirsiniz.

---

## 🇬🇧 English

### Contents

| File | Description |
|---|---|
| `veri/turkiye-kktc-yerlesim.json` | All records plus metadata (`_meta`: sources, field descriptions, counts) |
| `veri/turkiye-kktc-yerlesim.csv` | Same data as CSV (UTF-8, comma-separated) |
| `veri/turkiye-kktc-yerlesim.xlsx` | Same data as Excel (codes stored as text, leading zeros kept, filters on) |
| `veri/turkiye-kktc-yerlesim.sql` | MySQL / MariaDB: related tables `iller` (provinces) → `ilceler` (districts) → `yerlesimler` (settlements), utf8mb4_turkish_ci |
| `veri/posta-kodlari/<province>.json` | Lightweight per-province file: `{ "ilceler": { "<district>": { "<neighbourhood / village>": "<postal code>" } } }` for postal-code autofill in web forms |
| `veri/eslesme-raporu.txt` | Cross-source matching summary and unmatched records |
| `araclar/` | Scripts that rebuild the dataset |

### Fields

| Field | Description |
|---|---|
| `id` | Sequence number |
| `ulke` | Country: `TR` or `KKTC` (Northern Cyprus) |
| `plaka` | Province licence-plate code (`"07"`); none for KKTC |
| `il` | Province. For KKTC, the first-level district (Lefkoşa, Gazimağusa, Girne, Güzelyurt, İskele, Lefke) |
| `ilce` | District. For KKTC, the sub-district (bucak) |
| `semt` | PTT quarter / sub-district / town name |
| `belde` | Town (belde) the neighbourhood belongs to, per the Ministry of Interior |
| `tur` | Type: `mahalle` (neighbourhood), `köy` (village), `köy mahallesi` (quarter of a village, per PTT) or `bağlı` (hamlet / locality attached to a village, per the Ministry of Interior) |
| `ad` | Name |
| `koy` | Parent village for village quarters and hamlets |
| `posta_kodu` | Most frequent postal code of the unit (5 digits, string) |
| `diger_posta_kodlari` | Other postal codes found on the unit's streets |
| `eski_ad` | Former name of KKTC settlements |
| `kaynak` | Sources that contributed to the record |

### Sources

| Source | Used for |
|---|---|
| Ministry of Interior of Türkiye — [Inventory of Administrative Units](https://www.e-icisleri.gov.tr/Anasayfa/MulkiIdariBolumleri.aspx) | Official list of neighbourhoods, villages and hamlets (backbone) |
| Turkish Post (PTT) — [Postal Code Lookup](https://www.ptt.gov.tr/posta-kodu) | Current postal codes (aggregated from street level) |
| KKTC Postal Department — [Postal Codes](http://posta.gov.ct.tr/KURUMSAL/Posta-Kodlar%C4%B1) | KKTC districts, sub-districts, neighbourhoods, villages and postal codes |
| PTT postal code list (12 May 2021) | Quarter / sub-district names for Türkiye; fallback postal codes |
| Wikipedia — List of settlements in Northern Cyprus | Former names of KKTC settlements |

Precedence: Ministry of Interior (names and hierarchy) → current PTT (postal codes) → earlier PTT lists (quarters and fallback codes). Names are title-cased according to Turkish orthography.

`kaynak` values: `icisleri` · `ptt` (current PTT, exact name) · `ptt-benzer-ad` / `ptt-benzer-ad-zayif` (same district, spelling variant) · `ptt-2021` / `ptt-2024` (earlier PTT lists) · `ptt-2021-semt` / `ptt-2021-belde` · derived codes: `koyden` (hamlet → its village), `koy-mahallelerinden` (village → its quarters), `beldeden`, `semtten`, `ilceden` (code shared by all villages of the district) · `tahmini-ilce` (estimated) · `kktc-posta`. Every matching decision is listed in `veri/eslesme-raporu.txt`; `araclar/denetle.py` re-runs all checks.
### Rebuilding

1. `python araclar/icisleri_indir.py <dir>` — downloads the Ministry of Interior Excel lists (convert to CSV with LibreOffice).
2. `araclar/ptt_tara.js` — run in the browser console on the PTT lookup page; produces `ptt-guncel.json` (about one hour because of the server's rate limit).
3. `python araclar/yerlesim_birlestir.py <source_dir> veri <date>` — merges the sources.

### Limitations

- Postal codes follow the data published by PTT; a neighbourhood may have several codes (`diger_posta_kodlari`).
- Quarter (`semt`) names are matched from the 2021 PTT list and may be empty for newer units.
- The KKTC list is the Postal Department document dated 13 May 2019.
- The data is provided for information; official records of the relevant authority prevail.

### Support

If this dataset is useful to you, please support it by giving the repository a ⭐ **star** and leaving a short **thank-you note** in [Discussions](../../discussions). Use [issues](../../issues) for corrections and update requests.

---

**Hazırlayan / Maintainer:** [Mehmet Mesut YILMAZ](https://mehmetmesut.com) · Yeşil Dönüşüm Mühendisi © Creator M²Y

Kod MIT lisanslıdır. Veri, kaynak kurumların kamuya açık yayınlarından derlenmiştir; kaynak gösterilerek kullanılabilir.
Code is MIT licensed. Data is compiled from publicly available official publications; please cite the sources when using it.
