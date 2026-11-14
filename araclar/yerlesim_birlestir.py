"""Türkiye + KKTC yerleşim veritabanı: İçişleri (mülki idare), PTT (güncel + 2021 semt), KKTC Posta Dairesi, Vikipedi.

Kullanım: python yerlesim_birlestir.py <kaynak_dizini> <çıktı_dizini>
Kaynak dizinindeki dosyalar:
  icisleri-mahalle-GenelMahalleListesi.csv, icisleri-koy.csv, icisleri-bagli.csv   (İçişleri, Excel → CSV)
  ptt-guncel.json      (PTT posta kodu sorgu ucundan il → ilçe → mahalle → {pk: sokak sayısı})
  ptt-pk-20210512.csv  (PTT 12.05.2021 listesi; semt_bucak_belde sütunu)
  neighbourhoods.json  (PTT 2024 türevi; yalnız yedek posta kodu)
  kktc-posta-kodlari.txt (KKTC Posta Dairesi PDF → metin), kktc-wikitext.txt (Vikipedi)
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

KAYNAK = Path(sys.argv[1])
CIKTI = Path(sys.argv[2])
CIKTI.mkdir(parents=True, exist_ok=True)

BUYUK = str.maketrans({"i": "İ", "ı": "I"})
KUCUK = str.maketrans({"İ": "i", "I": "ı"})


def ust(s: str) -> str:
    return s.translate(BUYUK).upper()


def alt(s: str) -> str:
    return s.translate(KUCUK).lower()


def baslik(s: str) -> str:
    """AKPINAR → Akpınar; "100.YIL" → "100.Yıl"; "ALADAĞ-İLÇE" → "Aladağ-İlçe"."""
    s = re.sub(r"\s+", " ", s.strip())
    return re.sub(r"(^|[\s\-(./])(\w)", lambda m: m.group(1) + ust(m.group(2)), alt(s))


EKLER = re.compile(r"\s+(MAHALLESİ|MAHALLE|MAH\.?|KÖYÜ|KÖY)$")


def anahtar(s: str) -> str:
    """Eşleştirme anahtarı: büyük harf, ek yok, yalnız harf/rakam."""
    s = ust(s.strip())
    s = EKLER.sub("", s)
    return re.sub(r"[^0-9A-ZÇĞİÖŞÜÂÎÛ]", "", s)


def ilce_anahtar(s: str) -> str:
    return anahtar(s)


def satirlar(ad: str):
    with open(KAYNAK / ad, encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if r and r[0].strip().isdigit():
                yield [x.strip() for x in r if x.strip()]


# ── 1. İçişleri: mahalle, köy, bağlı ─────────────────────────────────────────
kayitlar = []  # dict listesi
for r in satirlar("icisleri-mahalle-GenelMahalleListesi.csv"):
    ad, yol = r[1], [p.strip() for p in r[2].split("->")]
    il = yol[0]
    if len(yol) == 2:  # "ADIYAMAN -> ADIYAMAN-İL MERKEZİ"
        ilce, belde = "MERKEZ", None
    else:
        ilce = yol[1]
        belde = None if yol[2].endswith("MERKEZİ") else yol[2]
    kayitlar.append({"il": il, "ilce": ilce, "belde": belde, "tur": "mahalle", "ad": ad, "koy": None})
for r in satirlar("icisleri-koy.csv"):
    kayitlar.append({"il": r[3], "ilce": r[2], "belde": None, "tur": "köy", "ad": r[1], "koy": None})
for r in satirlar("icisleri-bagli.csv"):
    yol = [p.strip() for p in r[2].split("->")]
    if len(yol) != 3:  # birkaç kurum kaydı (ör. büyükşehir su idaresi) yerleşim değildir
        continue
    if yol[2].endswith("MERKEZİ"):  # "BOLVADİN-İLÇE MERKEZİ": ilçe merkezine bağlı
        yol[2] = "İLÇE MERKEZİ"
    kayitlar.append({"il": yol[0], "ilce": yol[1], "belde": None, "tur": "bağlı", "ad": r[1], "koy": yol[2]})
icisleri_sayi = Counter(k["tur"] for k in kayitlar)

# ── 2. PTT güncel ───────────────────────────────────────────────────────────
KOY_BAGLI = re.compile(r"^(.*?)\s+MAH\.?\s*\((.*?)\s+KÖYÜ\)$")  # PTT 2021: "AHURİ MAH (SARIKAYA KÖYÜ)"
BELDE_MAH = re.compile(r"^(.*?)\s+MAH\.?\s*\((.*?)\s+BELDESİ\)$")
KOY_BAGLI_YENI = re.compile(r"^(.*?)\s*/\s*(.*?)\s+KÖYÜ$")      # PTT güncel: "AHURİ / SARIKAYA KÖYÜ"


def ayristir(mah: str):
    """PTT birim adı → (tür, ad, köy). Sondaki "MAH." / "MH" eki ve virgül gibi artıklar atılır."""
    u = ust(mah.strip())
    m = KOY_BAGLI.match(u) or KOY_BAGLI_YENI.match(u)
    if m and not temiz(m.group(1)):  # " / SAMANYOLU KÖYÜ": adsız köy mahallesi → köyün kendisi
        return "köy", temiz(m.group(2)), None
    if m:
        return "köy mahallesi", temiz(m.group(1)), temiz(m.group(2))
    if u.endswith(" KÖYÜ"):
        return "köy", temiz(u[: -len(" KÖYÜ")]), None
    return "mahalle", temiz(u), None


def temiz(s: str) -> str:
    s = re.sub(r"[\s,;:]+$", "", s.strip())
    s = re.sub(r"\s+(MAHALLESİ|MAH\.?|MH\.?)$", "", s)
    return s.strip(" ,")


ptt = json.loads((KAYNAK / "ptt-guncel.json").read_text(encoding="utf-8"))
ptt_kod = {}  # (il, ilce, tur, ad, koy) → Counter(pk)
ptt_ad = {}  # aynı anahtar → PTT'nin birebir yazımları ("CUMHURİYET / SARIYAPRAK KÖYÜ")
ptt_ham = []
for il in ptt["iller"].values():
    for ilce_ad, ilce in il["ilceler"].items():
        for mah, pkler in ilce["mahalle"].items():
            tur, ad, koy = ayristir(mah)
            if not anahtar(ad):  # adı boş PTT kaydı
                continue
            a = (anahtar(il["ad"]), ilce_anahtar(ilce_ad), tur, anahtar(ad), anahtar(koy or ""))
            ptt_kod.setdefault(a, Counter()).update({k: int(v) for k, v in pkler.items()})
            ptt_ad.setdefault(a, set()).add(mah.strip())
            ptt_ham.append((a, il["ad"], ilce_ad, tur, ad, koy))

# ── 3. PTT 2021 (semt) ve 2024 türevi (yedek posta kodu) ─────────────────────
semt = {}
pk_2021 = {}
pk_2021_semt = {}  # aynı adlı mahalleleri semt / belde adıyla ayırmak için
with open(KAYNAK / "ptt-pk-20210512.csv", encoding="utf-8", newline="") as f:
    for i, r in enumerate(csv.reader(f)):
        if i == 0 or len(r) < 5:
            continue
        il, ilce, sm, mah, pk = (x.strip() for x in r[:5])
        mb = BELDE_MAH.match(ust(mah))  # "CUMHURİYET MAH (KÖSECELİ BELDESİ)"
        if mb:
            mah, sm = mb.group(1), mb.group(2)
        tur, ad, koy = ayristir(mah)
        a =(anahtar(il), ilce_anahtar(ilce), tur, anahtar(ad), anahtar(koy or ""))
        semt[a] = sm
        pk_2021[a] = pk
        pk_2021_semt[a + (anahtar(sm),)] = pk
pk_2024 = {}
plaka = {}
for p, il, ilce, mah, pk in json.loads((KAYNAK / "neighbourhoods.json").read_text(encoding="utf-8")):
    plaka[anahtar(il)] = p
    pk_2024[(anahtar(il), ilce_anahtar(ilce), "mahalle", anahtar(mah), "")] = pk

# ── 4. Birleştir ─────────────────────────────────────────────────────────────
from difflib import SequenceMatcher

kullanilan = set()
cikti = []
benzer_cift = []
ic_anahtarlar = {(anahtar(k["il"]), ilce_anahtar(k["ilce"]), k["tur"], anahtar(k["ad"]), anahtar(k["koy"] or "")) for k in kayitlar}
# Benzer ad eşleştirme için: aynı il / ilçe / tür / köy içinde, İçişleri'nde tam eşi olmayan PTT anahtarları.
aday = defaultdict(list)
for a in ptt_kod:
    if a not in ic_anahtarlar:
        aday[(a[0], a[1], a[2], a[4])].append(a)


SADE = str.maketrans("ÇĞİÖŞÜÂÎÛ", "CGIOSUAIU")
YON_ONEKI = {"ASAGI", "YUKARI", "BUYUK", "KUCUK", "ESKI", "YENI", "ORTA", "A", "Y", "B", "K"}


SAYI_YAZI = {"100": "YÜZ", "75": "YETMİŞBEŞ", "29": "YİRMİDOKUZ", "23": "YİRMİÜÇ", "19": "ONDOKUZ", "15": "ONBEŞ", "10": "ON",
             "9": "DOKUZ", "8": "SEKİZ", "7": "YEDİ", "6": "ALTI", "5": "BEŞ", "4": "DÖRT", "3": "ÜÇ", "2": "İKİ", "1": "BİR"}
UNLU = str.maketrans("", "", "AEIİOÖUÜ")


def sayi_yaz(s: str) -> str:
    return re.sub(r"\d+", lambda m: SAYI_YAZI.get(m.group(0), m.group(0)), s)


def zayif_puan(x: str, y: str) -> float:
    """Yazım varyantı puanı: ilk harf aynı olmalı; tam ad ve ünsüz iskeleti benzerliğinin büyüğü."""
    x, y = sayi_yaz(x), sayi_yaz(y)
    if not x or not y or x[0] != y[0]:
        return 0.0
    tam = SequenceMatcher(None, x.translate(SADE), y.translate(SADE)).ratio()
    iskelet = SequenceMatcher(None, x.translate(UNLU).translate(SADE), y.translate(UNLU).translate(SADE)).ratio()
    return max(tam, iskelet)


def benzer_bul(a):
    """Yazım farkı (ULUCAMİ / ULUCAMİİ, HASAN TÜTÜN / KAYMAKAM HASAN TÜTÜN) için tek ve güçlü aday."""
    puanli = []
    for b in aday.get((a[0], a[1], a[2], a[4]), ()):
        if b in kullanilan:
            continue
        x, y = a[3].translate(SADE), b[3].translate(SADE)
        kisa, uzun = sorted((x, y), key=len)
        if uzun.replace(kisa, "", 1) in YON_ONEKI:  # Aşağı / Yukarı Elmalı ile Elmalı ayrı yerler olabilir
            continue
        if len(kisa) >= 5 and kisa in uzun and len(kisa) / len(uzun) >= 0.5:  # "KEPEZ CUMHURİYET" ↔ "CUMHURİYET"
            puanli.append((0.95, b))
        else:
            o = zayif_puan(a[3], b[3])
            if o >= 0.85:
                puanli.append((o, b))
    puanli.sort(reverse=True)
    if puanli and (len(puanli) == 1 or puanli[0][0] - puanli[1][0] >= 0.08):
        return puanli[0][1]
    return None


for k in kayitlar:
    a = (anahtar(k["il"]), ilce_anahtar(k["ilce"]), k["tur"], anahtar(k["ad"]), anahtar(k["koy"] or ""))
    kaynak = ["icisleri"]
    # Mükerrer önleme: İçişleri'nin bağlı birimi PTT'de "AD / KÖY KÖYÜ" (köy mahallesi) olarak geçer;
    # köyün kendi adını taşıyan köy mahallesi ("BAHRİ / BAHRİ KÖYÜ") köyün kendisidir.
    es = None
    pttadi = set()
    if k["tur"] == "bağlı":
        es = (a[0], a[1], "köy mahallesi", a[3], a[4])
    elif k["tur"] == "köy":
        es = (a[0], a[1], "köy mahallesi", a[3], a[3])
    if es in ptt_kod and es not in kullanilan:
        kullanilan.add(es)
        pttadi |= ptt_ad[es]
        if a not in ptt_kod:
            ptt_kod[a] = ptt_kod[es]
            ptt_ad.setdefault(a, set())
            semt.setdefault(a, semt.get(es))
    pkc = ptt_kod.get(a)
    b = None if pkc else benzer_bul(a)
    if b:
        pkc = ptt_kod[b]
        kullanilan.add(b)
        pttadi |= ptt_ad[b]
        kaynak.append("ptt-benzer-ad")
        benzer_cift.append((k["il"], k["ilce"], k["tur"], k["ad"], b[3], k["koy"] or ""))
        pkler = [p for p, _ in pkc.most_common()]
    elif pkc:
        kullanilan.add(a)
        pttadi |= ptt_ad.get(a, set())
        kaynak.append("ptt")
        pkler = [p for p, _ in pkc.most_common()]
    elif a in pk_2021:
        kaynak.append("ptt-2021")
        pkler = [pk_2021[a]]
    elif a in pk_2024:
        kaynak.append("ptt-2024")
        pkler = [pk_2024[a]]
    else:
        pkler = []
    sm = semt.get(a)
    # Aynı ilçede aynı adlı mahalleler (merkez ve belde): belde adıyla eşleşen 2021 kaydının kodu ve semti seçilir.
    if k["tur"] == "mahalle" and k["belde"]:
        pk_b = pk_2021_semt.get(a + (anahtar(k["belde"]),))
        if pk_b:
            pkler = [pk_b] + [p for p in pkler if p != pk_b]
            sm = k["belde"]
            kaynak.append("ptt-2021-belde")
    if sm and "ptt-2021" not in kaynak:
        kaynak.append("ptt-2021-semt")
    cikti.append({**k, "a": a, "semt": sm, "pk": pkler, "kaynak": kaynak, "ptt_adi": pttadi})

# Eksik tamamlama (türetme): bağlı birim köyünün, beldedeki mahalle beldesinin posta kodunu / semtini alır.
# Üst birim: köy; büyükşehirlerde eski köyler mahalle olduğundan mahalle de aranır (köy öncelikli).
koy_bilgi = {(c["a"][0], c["a"][1], c["a"][3]): c for c in cikti if c["tur"] == "mahalle"}
koy_bilgi.update({(c["a"][0], c["a"][1], c["a"][3]): c for c in cikti if c["tur"] == "köy"})
belde_pk = defaultdict(Counter)
for c in cikti:
    if c["tur"] == "mahalle" and c["belde"] and c["pk"]:
        belde_pk[(c["a"][0], c["a"][1], anahtar(c["belde"]))][c["pk"][0]] += 1
turetilen = Counter()
# İlçedeki bilinen köy kodları tek ve aynıysa kodsuz köylere verilir (PTT ilçe köylerine ortak kod verir).
ilce_koy_pk = defaultdict(set)
for c in cikti:
    if c["tur"] == "köy" and c["pk"]:
        ilce_koy_pk[(c["a"][0], c["a"][1])].add(c["pk"][0])
# PTT köyü yalnız köy mahalleleriyle listeliyorsa köyün kodu köy mahallelerinden alınır.
koy_mah_pk = defaultdict(Counter)
koy_mah_semt = {}
for a, *_ in ptt_ham:
    if a[2] == "köy mahallesi":
        koy_mah_pk[(a[0], a[1], a[4])].update(ptt_kod[a])
        if a in semt:
            koy_mah_semt[(a[0], a[1], a[4])] = semt[a]
koy_mah_pk_2021 = defaultdict(Counter)
for a, pk in pk_2021.items():
    if a[2] == "köy mahallesi":
        koy_mah_pk_2021[(a[0], a[1], a[4])][pk] += 1
        if a in semt:
            koy_mah_semt.setdefault((a[0], a[1], a[4]), semt[a])
for c in cikti:
    if c["tur"] == "köy" and not c["pk"]:
        anah = (c["a"][0], c["a"][1], c["a"][3])
        sayac = koy_mah_pk.get(anah) or koy_mah_pk_2021.get(anah)
        if sayac:
            c["pk"] = [p for p, _ in sayac.most_common()]
            c["kaynak"].append("koy-mahallelerinden" if anah in koy_mah_pk else "koy-mahallelerinden-2021")
            turetilen["köy posta kodu (köy mahallelerinden)"] += 1
            c["semt"] = c["semt"] or koy_mah_semt.get((c["a"][0], c["a"][1], c["a"][3]))

# Semtteki bilinen kodlar tek ve aynıysa semtin kodsuz köy / mahallelerine verilir.
semt_pk = defaultdict(set)
for c in cikti:
    if c["semt"] and c["pk"] and c["tur"] in ("mahalle", "köy"):
        semt_pk[(c["a"][0], c["a"][1], anahtar(c["semt"]))].add(c["pk"][0])
for c in cikti:
    if c["tur"] in ("mahalle", "köy") and not c["pk"] and c["semt"]:
        tek = semt_pk.get((c["a"][0], c["a"][1], anahtar(c["semt"])))
        if tek and len(tek) == 1:
            c["pk"] = [next(iter(tek))]
            c["kaynak"].append("semtten")
            turetilen[f"{c['tur']} posta kodu (semt ortak kodu)"] += 1
for c in cikti:
    tek = ilce_koy_pk.get((c["a"][0], c["a"][1]))
    if c["tur"] == "köy" and not c["pk"] and tek and len(tek) == 1:
        c["pk"] = [next(iter(tek))]
        c["kaynak"].append("ilceden")
        turetilen["köy posta kodu (ilçe ortak kodu)"] += 1
for c in cikti:
    if c["tur"] == "bağlı":
        koy = koy_bilgi.get((c["a"][0], c["a"][1], c["a"][4]))
        if koy and not c["pk"] and koy["pk"]:
            c["pk"] = [koy["pk"][0]]
            c["kaynak"].append("koyden")
            turetilen["bağlı posta kodu"] += 1
        if koy and not c["semt"] and koy["semt"]:
            c["semt"] = koy["semt"]
            turetilen["bağlı semt"] += 1
    elif c["tur"] == "mahalle" and c["belde"] and not c["pk"]:
        sayac = belde_pk.get((c["a"][0], c["a"][1], anahtar(c["belde"])))
        if sayac:
            c["pk"] = [sayac.most_common(1)[0][0]]
            c["kaynak"].append("beldeden")
            turetilen["belde mahallesi posta kodu"] += 1

# İçişleri'nde aynı ilçede aynı adla birden çok kayıt (ör. Efeler'de iki Yeniköy): PTT bunları
# "DALAMA BUCAĞI YENİKÖY" / "MERKEZ BUCAĞI YENİKÖY" gibi ayırır; adı içeren eşleşmemiş PTT kayıtları sırayla dağıtılır.
gruplar = defaultdict(list)
for c in cikti:
    if "icisleri" in c["kaynak"] and c["tur"] in ("mahalle", "köy"):
        gruplar[c["a"]].append(c)
ayni_ad_ayrilan = []
for a, grup in gruplar.items():
    if len(grup) < 2:
        continue
    adaylar = sorted(b for b in aday.get((a[0], a[1], a[2], a[4]), ()) if b not in kullanilan and a[3] in b[3] and b[3] != a[3])
    if a in ptt_kod:
        adaylar = [a] + adaylar  # tam adlı PTT kaydı da gruptaki birimlerden biridir
    if len(adaylar) < len(grup):
        continue
    # Eşleme: beldeye bağlı birim, PTT adında belde adı geçen kayda; beldesiz birim önce tam adlı kayda.
    def tam(s, ptt=False):  # ekleri atmadan karşılaştırma ("YENİ MAHALLE" ≠ "YENİ"); PTT'nin kendi eki "MAH." atılır
        s = ust(s)
        if ptt:
            s = re.sub(r"\s+(MAH\.?|KÖYÜ)$", "", s)
        return re.sub(r"[^0-9A-ZÇĞİÖŞÜÂÎÛ]", "", s)

    def esleme_puani(c, b):
        p = max(SequenceMatcher(None, tam(c["ad"]), tam(x, True)).ratio() for x in ptt_ad[b])
        if c["belde"] and anahtar(c["belde"]) in b[3]:
            p += 1
        return p

    puanlar = sorted(((esleme_puani(c, b), i, b) for i, c in enumerate(grup) for b in adaylar), key=lambda x: -x[0])
    eslesme, alinan_c, alinan_b = [], set(), set()
    for p, i, b in puanlar:  # en yüksek puanlı çiftten başlayarak her birime bir PTT kaydı
        if i in alinan_c or b in alinan_b:
            continue
        alinan_c.add(i)
        alinan_b.add(b)
        eslesme.append((grup[i], b))
    for c, b in eslesme:
        kullanilan.add(b)
        c["pk"] = [p for p, _ in ptt_kod[b].most_common()]
        c["ptt_adi"] = set(ptt_ad[b])
        c["kaynak"] = ["icisleri", "ptt-ayni-ad-ayrimi"]
        ayni_ad_ayrilan.append((c["il"], c["ilce"], c["ad"], " | ".join(sorted(ptt_ad[b]))))

# PTT'de olup İçişleri'nde eşi bulunmayanlar (ad farkı ya da yeni / kaldırılmış birim) ayrıca eklenir.
yalniz_ptt = []
for a, il, ilce, tur, ad, koy in ptt_ham:
    if a in kullanilan:
        continue
    kullanilan.add(a)
    yalniz_ptt.append(a)
    cikti.append({"il": il, "ilce": ilce, "belde": None, "tur": tur, "ad": ad, "koy": koy, "a": a,
                  "semt": semt.get(a), "pk": [p for p, _ in ptt_kod[a].most_common()], "kaynak": ["ptt"],
                  "ptt_adi": set(ptt_ad[a])})

# Son çare (posta kodu boş kalmaz): 1) aynı ilçede eşi bulunmamış tek PTT mahallesi ile zayıf benzerlik,
# 2) aynı belde / ilçe ve türdeki birimlerin en yaygın kodu. Kaynakta "tahmini" olarak işaretlenir.
def yaygin(ölcut):
    sayac = defaultdict(Counter)
    for c in cikti:
        if c["pk"] and "tahmini" not in " ".join(c["kaynak"]):
            sayac[ölcut(c)][c["pk"][0]] += 1
    return sayac


bos = [c for c in cikti if not c["pk"]]
zayif_eslesen = set()
zayif_cift = []
yalniz_set = set(yalniz_ptt)
for c in bos:
    if c["tur"] != "mahalle":
        continue
    kalan = [b for b in aday.get((c["a"][0], c["a"][1], "mahalle", ""), ()) if b in yalniz_set and b not in zayif_eslesen]
    puan = sorted(((zayif_puan(c["a"][3], b[3]), b) for b in kalan), reverse=True)
    if puan and puan[0][0] >= 0.75 and (len(puan) == 1 or puan[0][0] - puan[1][0] >= 0.15):
        c["pk"] = [p for p, _ in ptt_kod[puan[0][1]].most_common()]
        c["kaynak"].append("ptt-benzer-ad-zayif")
        c["ptt_adi"] |= ptt_ad[puan[0][1]]
        kullanilan.add(puan[0][1])
        zayif_eslesen.add(puan[0][1])
        zayif_cift.append((c["il"], c["ilce"], c["ad"], puan[0][1][3], round(puan[0][0], 2), c["pk"][0]))
        turetilen["mahalle posta kodu (zayıf benzerlik)"] += 1
# Zayıf benzerlikle İçişleri kaydına bağlanan PTT kaydı ayrı satır olarak kalmaz (mükerrer olur).
cikti = [c for c in cikti if not (c["kaynak"] == ["ptt"] and c["a"] in zayif_eslesen)]
belde_say = yaygin(lambda c: (c["a"][0], c["a"][1], "mahalle", anahtar(c.get("belde") or "")))
tur_say = yaygin(lambda c: (c["a"][0], c["a"][1], c["tur"]))
for c in cikti:
    if c["pk"]:
        continue
    adaylar = []
    if c["tur"] == "mahalle" and c.get("belde"):
        adaylar.append(belde_say.get((c["a"][0], c["a"][1], "mahalle", anahtar(c["belde"]))))
    if c["tur"] == "bağlı":
        if anahtar(c["koy"] or "") == anahtar("İLÇE MERKEZİ"):
            adaylar.append(belde_say.get((c["a"][0], c["a"][1], "mahalle", "")))
        adaylar.append(tur_say.get((c["a"][0], c["a"][1], "köy")))
    adaylar.append(tur_say.get((c["a"][0], c["a"][1], c["tur"])))
    adaylar.append(tur_say.get((c["a"][0], c["a"][1], "mahalle")))
    sayac = next((s for s in adaylar if s), None)
    if sayac:
        c["pk"] = [sayac.most_common(1)[0][0]]
        c["kaynak"].append("tahmini-ilce")
        turetilen[f"{c['tur']} posta kodu (tahmini, ilçe / belde en yaygın kod)"] += 1

# ── 5. KKTC ─────────────────────────────────────────────────────────────────
KKTC_SATIR = re.compile(r"^KKTC\s+(\S.*?)\s{2,}(\S.*?)\s{2,}(\S.*?)\s{2,}(\d{5})\s*$")
kktc = []
for satir in (KAYNAK / "kktc-posta-kodlari.txt").read_text(encoding="utf-8").splitlines():
    m = KKTC_SATIR.match(satir.strip())
    if not m:
        continue
    ilce, bucak, birim, pk = m.groups()
    ilce = {"GAZİ MAĞUSA": "GAZİMAĞUSA"}.get(re.sub(r"\s+", " ", ilce), ilce)  # resmî yazım
    tur = "köy" if ust(birim).endswith(("KÖYÜ", "KÖY")) else "mahalle"
    ad = EKLER.sub("", ust(birim)).strip()
    kktc.append({"ilce": ilce, "bucak": bucak, "tur": tur, "ad": ad, "pk": pk, "ham": re.sub(r"\s+", " ", birim.strip())})
eski_ad = {}
for m in re.finditer(r"\*\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]\s*(?:-\s*([^\n]+))?", (KAYNAK / "kktc-wikitext.txt").read_text(encoding="utf-8")):
    yeni = (m.group(2) or m.group(1)).split(" - ")[0].strip()
    eski = (m.group(3) or "").strip() or ((m.group(2) or "").split(" - ")[1].strip() if " - " in (m.group(2) or "") else "")
    if eski and anahtar(eski) != anahtar(yeni):
        eski_ad[anahtar(yeni)] = eski
for k in kktc:
    cikti.append({"ulke": "KKTC", "il": k["ilce"], "ilce": k["bucak"], "belde": None, "tur": k["tur"], "ad": k["ad"],
                  "koy": None, "semt": k["bucak"], "pk": [k["pk"]], "kaynak": ["kktc-posta"],
                  "eski_ad": eski_ad.get(anahtar(k["ad"])), "ptt_adi": {k["ham"]}})

# ── 6. Yaz ──────────────────────────────────────────────────────────────────
def ad_duzenle(ad: str, tur: str) -> str:
    """Kısaltma noktalaması ("D:Ü:ÇİFTLİĞİ", "DEV,ÜR.") noktaya çevrilir; mahalle adındaki "Mahallesi" eki atılır (tür ayrı sütunda)."""
    s = re.sub(r"(?<=\w)[:,](?=\w)", ".", ad.strip())
    if tur in ("mahalle", "köy mahallesi"):
        s = re.sub(r"\s+(MAHALLESİ|MAH\.?)$", "", ust(s)) if s.isupper() else re.sub(r"\s+(Mahallesi|Mah\.?)$", "", s)
    return baslik(s)


def kayit(c: dict) -> dict:
    ulke = c.get("ulke", "TR")
    return {
        "ulke": ulke,
        "plaka": plaka.get(anahtar(c["il"])) if ulke == "TR" else None,
        "il": baslik(c["il"]),
        "ilce": baslik(c["ilce"]),
        "semt": baslik(c["semt"]) if c.get("semt") else None,
        "belde": baslik(c["belde"]) if c.get("belde") else None,
        "tur": c["tur"],
        "ad": ad_duzenle(c["ad"], c["tur"]),
        "koy": baslik(c["koy"]) if c.get("koy") else None,
        "posta_kodu": c["pk"][0] if c["pk"] else None,
        "diger_posta_kodlari": c["pk"][1:] or None,
        "eski_ad": c.get("eski_ad"),
        "ptt_adi": " | ".join(sorted(c.get("ptt_adi") or [])) or None,
        "kaynak": c["kaynak"],
    }


SIRA = {"mahalle": 0, "köy": 1, "köy mahallesi": 2, "bağlı": 3}
tum = sorted((kayit(c) for c in cikti), key=lambda r: (r["ulke"] != "TR", r["plaka"] or "99", alt(r["il"]), alt(r["ilce"]),
                                                       SIRA[r["tur"]], alt(r["koy"] or ""), alt(r["ad"])))
# PTT yazım hatası düzeltme: ülke genelinde çok yaygın bir addan tek harf farklı, nadir PTT yazımı
# ("CUMHURRİYET" → Cumhuriyet). Yerleşim Adı düzeltilir; PTT Adı sütunu PTT yazımını aynen korur.
SAPKALI = {frozenset(p) for p in ("uü", "sş", "cç", "oö", "gğ", "iı")}


def tek_harf_farkli(x: str, y: str) -> bool:
    """x (PTT yazımı) ile y (yaygın ad) arasında tek bir YAZIM HATASI türünde fark var mı?
    İzin verilen: çift harf (cumhurriyet), Türkçe harf (hurriyet / karsıyaka), sonda eksik / fazla harf (yeşilyur),
    boşluk (orta köy). İlk harf farkı (çerkez / merkez) ve diğer harf değişimleri düzeltilmez."""
    if abs(len(x) - len(y)) > 1 or x == y:
        return False
    i = 0
    while i < min(len(x), len(y)) and x[i] == y[i]:
        i += 1
    if i == 0:
        return False
    if len(x) == len(y):  # değişim: yalnız Türkçe harf çifti
        return x[i + 1:] == y[i + 1:] and frozenset((x[i], y[i])) in SAPKALI
    uzun, kisa = (x, y) if len(x) > len(y) else (y, x)
    if uzun[i + 1:] != kisa[i:]:
        return False
    fazla = uzun[i]
    return fazla == " " or i == len(kisa) or fazla == uzun[i - 1]  # boşluk, sonda harf, çift harf


ad_sikligi = Counter(alt(r["ad"]) for r in tum if r["ulke"] == "TR")
yaygin_adlar = defaultdict(list)
for ad, n in ad_sikligi.items():
    if n >= 100 and len(ad) >= 6:
        yaygin_adlar[len(ad)].append(ad)
duzeltilen = []
for r in tum:
    if r["kaynak"] != ["ptt"] or ad_sikligi[alt(r["ad"])] > 2 or len(r["ad"]) < 6:
        continue
    x = alt(r["ad"])
    adaylar = [y for n in (len(x) - 1, len(x), len(x) + 1) for y in yaygin_adlar.get(n, ()) if tek_harf_farkli(x, y)]
    if len(adaylar) == 1:
        duzeltilen.append((r["il"], r["ilce"], r["koy"] or "", r["ad"], baslik(adaylar[0])))
        r["ad"] = baslik(adaylar[0])
        r["kaynak"] = r["kaynak"] + ["ad-duzeltildi"]

# Birebir aynı satırlar (ülke, il, ilçe, belde, tür, köy, ad) tek kayda indirilir. İçişleri'nin kendi listesinde
# aynı ilçede aynı adla iki ayrı birim varsa (resmî kayıt) ikisi de korunur; PTT yazımları kaybolmaz.
gorulen = {}
tekil = []
icisleri_cift = []
for r in tum:
    anah = (r["ulke"], r["il"], r["ilce"], r["belde"], r["tur"], r["koy"], alt(r["ad"]))
    ilk = gorulen.get(anah)
    if ilk is None:
        gorulen[anah] = r
        tekil.append(r)
        continue
    if "icisleri" in ilk["kaynak"] and "icisleri" in r["kaynak"]:
        if (ilk["ptt_adi"] or "") != (r["ptt_adi"] or ""):  # PTT ayrı birim olarak tanıyor (ör. Efeler'deki iki Yeniköy)
            tekil.append(r)
            continue
        # İçişleri aynı birimi iki kez listelemiş; PTT'de tek karşılık: tek satır, kaynakta işaretli.
        icisleri_cift.append((r["il"], r["ilce"], r["tur"], r["ad"], r["koy"] or "", r["ptt_adi"] or ""))
        if "icisleri-iki-kez" not in ilk["kaynak"]:
            ilk["kaynak"] = ilk["kaynak"] + ["icisleri-iki-kez"]
        continue
    hedef, diger = (r, ilk) if "icisleri" in r["kaynak"] else (ilk, r)
    adlar = set(filter(None, (ilk["ptt_adi"] or "").split(" | "))) | set(filter(None, (r["ptt_adi"] or "").split(" | ")))
    hedef["ptt_adi"] = " | ".join(sorted(adlar)) or None
    if hedef is r:
        tekil[tekil.index(ilk)] = r
        gorulen[anah] = r
birebir_mukerrer = len(tum) - len(tekil)
tum = tekil
for i, r in enumerate(tum, 1):
    r["id"] = i
sayilar = {
    "toplam": len(tum),
    "tr": dict(Counter(r["tur"] for r in tum if r["ulke"] == "TR")),
    "kktc": dict(Counter(r["tur"] for r in tum if r["ulke"] == "KKTC")),
    "icisleri_kaynak": dict(icisleri_sayi),
    "posta_kodu_yok": sum(1 for r in tum if not r["posta_kodu"]),
    "yalniz_ptt": len(yalniz_ptt),
    "semt_var": sum(1 for r in tum if r["semt"]),
    "turetilen": dict(turetilen),
    "birebir_mukerrer_dusulen": birebir_mukerrer,
    "ptt_yazim_duzeltilen": len(duzeltilen),
    "ayni_ad_ptt_ile_ayrilan": len(ayni_ad_ayrilan),
    "icisleri_ayni_ad_iki_kayit": len(icisleri_cift),
}
meta = {
    "ad": "Türkiye ve KKTC yerleşim yerleri ve posta kodları",
    "olusturma": sys.argv[3] if len(sys.argv) > 3 else None,
    "kaynaklar": {
        "icisleri": "T.C. İçişleri Bakanlığı, Mülki İdare Bölümleri Envanteri (e-icisleri.gov.tr) — mahalle, köy, bağlı listeleri",
        "ptt": "PTT posta kodu sorgulama (ptt.gov.tr/posta-kodu) — güncel posta kodları",
        "ptt-2021": "PTT posta kodu listesi 12.05.2021 — semt / bucak / belde ve yedek posta kodu",
        "ptt-2024": "PTT listesinin 31.03.2024 türevi (MIT) — yedek posta kodu",
        "kktc-posta": "KKTC Posta Dairesi, Uluslararası Posta Kodları (13.05.2019)",
        "vikipedi": "Vikipedi, KKTC'deki yerleşim yerleri listesi — eski adlar",
    },
    "alanlar": {
        "ulke": "TR | KKTC", "plaka": "il plaka kodu (KKTC: yok)",
        "il": "il (KKTC: ilçe — birinci düzey idari birim)", "ilce": "ilçe (KKTC: bucak)",
        "semt": "PTT semt / bucak / belde adı", "belde": "İçişleri'ne göre mahallenin bağlı olduğu belde",
        "tur": "mahalle | köy | köy mahallesi (PTT) | bağlı (İçişleri: mezra, mevki)", "koy": "köy mahallesinin / bağlı birimin köyü", "posta_kodu": "en yaygın posta kodu",
        "diger_posta_kodlari": "aynı birimde geçen diğer posta kodları (sokak bazında)",
        "eski_ad": "KKTC eski (Rumca) adı",
        "ptt_adi": "PTT'deki (KKTC: Posta Dairesi listesindeki) birebir yazım; birden çoksa ' | ' ile ayrılır",
        "kaynak": "kaydı besleyen kaynaklar",
    },
    "sayilar": sayilar,
}
(CIKTI / "turkiye-kktc-yerlesim.json").write_text(json.dumps({"_meta": meta, "kayitlar": tum}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
BASLIKLAR = ["Sıra No", "Ülke", "Plaka Kodu", "İl", "İlçe", "Semt", "Belde", "Tür", "Yerleşim Adı", "Bağlı Olduğu Köy",
             "Posta Kodu", "PTT Adı", "Diğer Posta Kodları", "Eski Adı", "Kaynak"]


def satir(r: dict) -> list:
    return [r["id"], r["ulke"], r["plaka"], r["il"], r["ilce"], r["semt"], r["belde"], TUR_ADI[r["tur"]], r["ad"], r["koy"],
            r["posta_kodu"], r["ptt_adi"], " ".join(r["diger_posta_kodlari"] or []) or None, r["eski_ad"], " ".join(r["kaynak"])]


TUR_ADI = {"mahalle": "Mahalle", "köy": "Köy", "köy mahallesi": "Köy Mahallesi", "bağlı": "Bağlı Birim"}
with open(CIKTI / "turkiye-kktc-yerlesim.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(BASLIKLAR)
    for r in tum:
        w.writerow(["" if v is None else v for v in satir(r)])

# CRM için il başına küçük dosya: {"ilceler": {ilçe: {mahalle/köy adı: posta kodu}}}
il_dizin = CIKTI / "posta-kodlari"
il_dizin.mkdir(exist_ok=True)
DOSYA = str.maketrans("çğıöşüâîû", "cgiosuaiu")
gruplar = defaultdict(lambda: defaultdict(dict))
for r in tum:
    if r["posta_kodu"] and r["tur"] != "bağlı":
        gruplar[r["il"]][r["ilce"]].setdefault(r["ad"], r["posta_kodu"])
for il, ilceler in gruplar.items():
    dosya = re.sub(r"[^a-z0-9]+", "-", alt(il).translate(DOSYA)).strip("-")
    (il_dizin / f"{dosya}.json").write_text(json.dumps({"_kaynak": "İçişleri + PTT birleşik", "ilceler": ilceler}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

# ── SQL (MySQL / MariaDB): iller → ilceler → yerlesimler ─────────────────────
def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


il_id, ilce_id = {}, {}
for r in tum:
    il_id.setdefault((r["ulke"], r["il"]), (len(il_id) + 1, r["plaka"]))
    ilce_id.setdefault((r["ulke"], r["il"], r["ilce"]), len(ilce_id) + 1)
with open(CIKTI / "turkiye-kktc-yerlesim.sql", "w", encoding="utf-8", newline="\n") as f:
    f.write(f"-- {meta['ad']} · {meta['olusturma'] or ''}\n-- Kaynaklar: " + "; ".join(meta["kaynaklar"].values()) + "\n")
    f.write("SET NAMES utf8mb4;\n\nDROP TABLE IF EXISTS yerlesimler;\nDROP TABLE IF EXISTS ilceler;\nDROP TABLE IF EXISTS iller;\n\n")
    f.write("CREATE TABLE iller (\n  id SMALLINT UNSIGNED PRIMARY KEY,\n  ulke CHAR(4) NOT NULL COMMENT 'TR | KKTC',\n"
            "  plaka CHAR(2) NULL COMMENT 'il plaka kodu',\n  ad VARCHAR(60) NOT NULL,\n  UNIQUE KEY uk_iller (ulke, ad)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;\n\n")
    f.write("CREATE TABLE ilceler (\n  id SMALLINT UNSIGNED PRIMARY KEY,\n  il_id SMALLINT UNSIGNED NOT NULL,\n  ad VARCHAR(80) NOT NULL,\n"
            "  UNIQUE KEY uk_ilceler (il_id, ad),\n  CONSTRAINT fk_ilce_il FOREIGN KEY (il_id) REFERENCES iller (id)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;\n\n")
    f.write("CREATE TABLE yerlesimler (\n  id INT UNSIGNED PRIMARY KEY,\n  ilce_id SMALLINT UNSIGNED NOT NULL,\n  semt VARCHAR(80) NULL,\n"
            "  belde VARCHAR(80) NULL,\n  tur ENUM('mahalle','köy','köy mahallesi','bağlı') NOT NULL,\n  ad VARCHAR(120) NOT NULL,\n  koy VARCHAR(120) NULL,\n"
            "  posta_kodu CHAR(5) NULL,\n  ptt_adi VARCHAR(400) NULL COMMENT 'PTT / KKTC Posta Dairesi yazımı',\n  diger_posta_kodlari VARCHAR(120) NULL,\n  eski_ad VARCHAR(120) NULL,\n  kaynak VARCHAR(80) NOT NULL,\n"
            "  KEY ix_ilce_ad (ilce_id, ad),\n  KEY ix_posta_kodu (posta_kodu),\n  CONSTRAINT fk_yerlesim_ilce FOREIGN KEY (ilce_id) REFERENCES ilceler (id)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;\n\n")
    f.write("INSERT INTO iller (id, ulke, plaka, ad) VALUES\n" + ",\n".join(
        f"({i}, {q(u)}, {q(p)}, {q(a)})" for (u, a), (i, p) in il_id.items()) + ";\n\n")
    f.write("INSERT INTO ilceler (id, il_id, ad) VALUES\n" + ",\n".join(
        f"({i}, {il_id[(u, il)][0]}, {q(a)})" for (u, il, a), i in ilce_id.items()) + ";\n\n")
    for bas in range(0, len(tum), 1000):
        parca = tum[bas:bas + 1000]
        f.write("INSERT INTO yerlesimler (id, ilce_id, semt, belde, tur, ad, koy, posta_kodu, ptt_adi, diger_posta_kodlari, eski_ad, kaynak) VALUES\n")
        f.write(",\n".join(
            f"({r['id']}, {ilce_id[(r['ulke'], r['il'], r['ilce'])]}, {q(r['semt'])}, {q(r['belde'])}, {q(r['tur'])}, {q(r['ad'])}, {q(r['koy'])}, "
            f"{q(r['posta_kodu'])}, {q(r['ptt_adi'])}, {q(' '.join(r['diger_posta_kodlari'] or []) or None)}, {q(r['eski_ad'])}, {q(' '.join(r['kaynak']))})"
            for r in parca) + ";\n")

# ── XLSX: kodlar metin (baştaki sıfır korunur), başlık sabit, süzgeç açık ──────
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook(write_only=False)
ws = wb.active
ws.title = "Yerleşimler"
ws.append(BASLIKLAR)
for r in tum:
    ws.append(satir(r))
for sutun in ("C", "K", "M"):
    for hucre in ws[sutun][1:]:
        hucre.number_format = "@"
for h in ws[1]:
    h.font = Font(bold=True, color="FFFFFF")
    h.fill = PatternFill("solid", fgColor="003566")
for harf, gen in zip("ABCDEFGHIJKLMNO", (8, 7, 7, 16, 18, 18, 16, 13, 28, 20, 11, 34, 18, 14, 30)):
    ws.column_dimensions[harf].width = gen
ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions
ks = wb.create_sheet("Kaynaklar")
ks.append(["Kod", "Kaynak"])
for k, v in meta["kaynaklar"].items():
    ks.append([k, v])
ks.append([])
for k, v in sayilar.items():
    ks.append([k, json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v])
ks.column_dimensions["A"].width = 22
ks.column_dimensions["B"].width = 110
wb.properties.creator = "Mehmet Mesut YILMAZ"
wb.properties.lastModifiedBy = "Mehmet Mesut YILMAZ"
wb.properties.title = meta["ad"]
wb.properties.language = "tr-TR"
wb.save(CIKTI / "turkiye-kktc-yerlesim.xlsx")

# Eşleşme raporu
with open(CIKTI / "eslesme-raporu.txt", "w", encoding="utf-8") as f:
    f.write(json.dumps(sayilar, ensure_ascii=False, indent=1) + "\n\n")
    f.write("== Tahmini posta kodu verilen kayıtlar (PTT'de karşılığı bulunamadı; ilçe / belde en yaygın kodu)\n")
    for r in tum:
        if "tahmini-ilce" in r["kaynak"]:
            f.write(f"{r['il']} / {r['ilce']} / {r['tur']} / {r['ad']} / {r['koy'] or ''} → {r['posta_kodu']}\n")
    f.write("\n== PTT yazım hatası düzeltilen adlar (il / ilçe / köy / PTT yazımı → düzeltilmiş ad)\n")
    for x in duzeltilen:
        f.write(" / ".join(map(str, x)) + "\n")
    f.write("\n== İçişleri'nde aynı ilçede aynı adlı birimler, PTT adıyla ayrıldı (il / ilçe / ad / PTT adı)\n")
    for x in ayni_ad_ayrilan:
        f.write(" / ".join(map(str, x)) + "\n")
    f.write("\n== İçişleri listesinde aynı ilçede aynı adla iki kez geçen, PTT'de tek karşılığı olan birimler (tek satıra indirildi; kaynak: icisleri-iki-kez)\n")
    for x in icisleri_cift:
        f.write(" / ".join(map(str, x)) + "\n")
    f.write("\n== Zayıf benzerlikle eşleşenler (İçişleri adı → PTT adı, benzerlik, kod)\n")
    for cift in zayif_cift:
        f.write(" / ".join(map(str, cift)) + "\n")
    f.write("\n== Benzer adla eşleşenler (il / ilçe / tür / İçişleri adı → PTT adı / köy)\n")
    for cift in benzer_cift:
        f.write(" / ".join(map(str, cift)) + "\n")
    f.write("\n== İçişleri'nde karşılığı olmayan PTT kayıtları (ayrı satır olarak eklendi; ilk 500)\n")
    for a in [x for x in yalniz_ptt if x not in zayif_eslesen][:500]:
        f.write(" / ".join(a) + "\n")
print(json.dumps(sayilar, ensure_ascii=False))
