"""Yerleşim veritabanının ayrıntılı denetimi. Kullanım: python denetle.py <veri_dizini>"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
V = Path(sys.argv[1])
k = json.loads((V / "turkiye-kktc-yerlesim.json").read_text(encoding="utf-8"))["kayitlar"]
hatalar = defaultdict(list)

TR_HARF = re.compile(r"^[0-9A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû .'()/\-]+$")
for r in k:
    pk = r["posta_kodu"]
    if not pk:
        hatalar["posta kodu boş"].append(r)
    elif not re.fullmatch(r"\d{5}", pk):
        hatalar["posta kodu 5 hane değil"].append(r)
    elif r["ulke"] == "TR" and pk[:2] != r["plaka"]:
        hatalar["posta kodu plaka ile başlamıyor"].append(r)
    elif r["ulke"] == "KKTC" and not pk.startswith("99"):
        hatalar["KKTC kodu 99 ile başlamıyor"].append(r)
    for alan in ("il", "ilce", "ad", "semt", "belde", "koy"):
        v = r[alan]
        if v is None:
            continue
        if "  " in v or v != v.strip():
            hatalar[f"{alan}: fazla boşluk"].append(r)
        if not TR_HARF.match(v):
            hatalar[f"{alan}: beklenmeyen karakter"].append(r)
        if re.search(r"\b(Mah|Mahallesi|Köyü)\.?$", v) and alan in ("ad", "koy"):
            hatalar[f"{alan}: tür eki kalmış"].append(r)
        if re.search(r"[ÃÅÄ]", v) or "�" in v:
            hatalar[f"{alan}: bozuk kodlama"].append(r)
    if r["tur"] in ("bağlı", "köy mahallesi") and not r["koy"]:
        hatalar["bağlı / köy mahallesi: köy boş"].append(r)
    if r["ulke"] == "TR" and not re.fullmatch(r"\d{2}", r["plaka"] or ""):
        hatalar["plaka eksik"].append(r)

anah = Counter((r["ulke"], r["il"], r["ilce"], r["belde"], r["tur"], r["koy"], r["ad"].casefold()) for r in k)
for a, n in anah.items():
    if n > 1:
        hatalar["birebir mükerrer"].append({"anahtar": a, "adet": n})

# Bağlı birimin köyü aynı ilçede köy ya da mahalle olarak bulunmalı
ust = {(r["il"], r["ilce"], r["ad"].casefold()) for r in k if r["tur"] in ("köy", "mahalle")}
for r in k:
    if r["tur"] == "bağlı" and r["koy"] != "İlçe Merkezi" and (r["il"], r["ilce"], (r["koy"] or "").casefold()) not in ust:
        hatalar["bağlı birimin köyü listede yok"].append(r)

# Tüm TR kodları, bugün canlı PTT'den çekilen verideki kendi ilçesinin kod kümesinde olmalı.
if len(sys.argv) > 2:
    BB = str.maketrans({"i": "İ", "ı": "I"})
    ptt = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    ilce_kod = defaultdict(set)
    for il in ptt["iller"].values():
        for ad, c in il["ilceler"].items():
            for kodlar in c["mahalle"].values():
                ilce_kod[(il["ad"], ad)].update(kodlar)
    for r in k:
        if r["ulke"] == "TR" and r["posta_kodu"] not in ilce_kod[(r["il"].translate(BB).upper(), r["ilce"].translate(BB).upper())]:
            hatalar["kod canlı PTT'de bu ilçede yok"].append(r)

il_tr = {r["il"] for r in k if r["ulke"] == "TR"}
ilce_tr = {(r["il"], r["ilce"]) for r in k if r["ulke"] == "TR"}
plaka_il = defaultdict(set)
for r in k:
    if r["ulke"] == "TR":
        plaka_il[r["plaka"]].add(r["il"])
print(f"Kayıt: {len(k)} · TR il: {len(il_tr)} · TR ilçe: {len(ilce_tr)} · plaka: {len(plaka_il)}")
print("Bir plakada birden çok il:", {p: v for p, v in plaka_il.items() if len(v) > 1} or "yok")
print("Tür dağılımı:", dict(Counter((r["ulke"], r["tur"]) for r in k)))
print("Kaynak dağılımı (posta kodu):", Counter(next((x for x in r["kaynak"] if x != "icisleri" and not x.endswith("semt")), "yok") for r in k).most_common())
print()
if not hatalar:
    print("HATA YOK")
for ad, liste in sorted(hatalar.items(), key=lambda x: -len(x[1])):
    print(f"[{len(liste)}] {ad}")
    for r in liste[:5]:
        print("    ", {x: r.get(x) for x in ("ulke", "plaka", "il", "ilce", "belde", "tur", "koy", "ad", "posta_kodu", "kaynak", "anahtar", "adet") if r.get(x) is not None})
