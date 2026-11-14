"""İçişleri Bakanlığı mülki idare listelerini (Excel) resmî sayfanın form gönderimiyle indirir."""
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

URL = "https://www.e-icisleri.gov.tr/Anasayfa/MulkiIdariBolumleri.aspx"
HEDEF = Path(sys.argv[1])
DUGMELER = {
    "icisleri-koy.xls": "ImageButton7",
    "icisleri-bagli.xls": "ImageButton9",
    "icisleri-ilce.xls": "ImageButton3",
    "icisleri-belde.xls": "ImageButton10",
    "icisleri-il.xls": "ImageButton5",
    "icisleri-buyuksehir-ilce.xls": "ImageButton2",
}

jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
op.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")]


def gizli_alanlar(html: str) -> dict:
    return {m[0]: m[1] for m in re.findall(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]*value="([^"]*)"', html)}


for ad, dugme in DUGMELER.items():
    sayfa = op.open(URL, timeout=60).read().decode("utf-8", "replace")
    veri = gizli_alanlar(sayfa)
    on = "ctl00$cph1$CografiBirimControl$"
    veri.update({on + "DropDownListIl": "-1", on + dugme + ".x": "5", on + dugme + ".y": "5"})
    yanit = op.open(URL, data=urllib.parse.urlencode(veri).encode(), timeout=300)
    icerik = yanit.read()
    tur = yanit.headers.get("Content-Type", "")
    if not icerik.startswith(b"\xd0\xcf\x11\xe0"):
        print(f"{ad}: Excel değil ({tur}, {len(icerik)} bayt)")
        continue
    (HEDEF / ad).write_bytes(icerik)
    print(f"{ad}: {len(icerik)} bayt")
