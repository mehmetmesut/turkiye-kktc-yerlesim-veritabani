/**
 * PTT posta kodu sorgu sayfasından (https://www.ptt.gov.tr/posta-kodu) tüm il → ilçe → mahalle → posta kodu verisini toplar.
 * Kullanım: sayfayı tarayıcıda açın, geliştirici konsoluna bu dosyanın içeriğini yapıştırın; bittiğinde
 * "ptt-guncel.json" dosyası iner. Sunucu hız sınırı uyguladığı için istekler arası bekleme vardır (~1 saat sürer).
 * Çıktı: { iller: { <ilKodu>: { kod, ad, ilceSayisi, ilceler: { <ilçe>: { kod, satir, mahalle: { <ad>: { <pk>: sokakSayisi } } } } } } }
 */
;(async () => {
  const bekle = (ms) => new Promise((r) => setTimeout(r, ms))
  const ilSel = document.getElementById('il-select')
  const ilceOku = () => [...document.getElementById('ilce-select').options].filter((x) => x.value).map((x) => [x.value, x.text])
  const PK = { iller: {}, hata: [], uyusmaz: [] }
  let onceki = ''

  const ilceleriYukle = async (ilKodu) => {
    for (let deneme = 0; deneme < 4; deneme++) {
      ilSel.value = ilKodu
      ilSel.dispatchEvent(new Event('change', { bubbles: true }))
      for (let k = 0; k < 60; k++) {
        await bekle(250)
        const liste = ilceOku()
        const imza = liste.map((x) => x[0]).join(',')
        if (liste.length && imza !== onceki) {
          onceki = imza
          return liste
        }
      }
      await bekle(15000) // hız sınırı: bekleyip yeniden dene
    }
    return []
  }

  for (const o of [...ilSel.options].filter((x) => x.value)) {
    const ilceler = await ilceleriYukle(o.value)
    const il = { kod: o.value, ad: o.text, ilceSayisi: ilceler.length, ilceler: {} }
    PK.iller[o.value] = il
    if (!ilceler.length) PK.hata.push([o.text, 'ilçe listesi yok'])
    for (const [ik, iad] of ilceler) {
      let ok = false
      for (let d = 0; d < 5 && !ok; d++) {
        try {
          const r = await fetch('/api/posta-kodu', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'postakodu', il_kodu: o.value, ilce_kodu: ik }),
          })
          if (!r.ok) throw new Error('durum ' + r.status)
          const m = {}
          let satir = 0
          for (const x of await r.json()) {
            satir++
            if (x.İl_Adi !== o.text || x.İlce_Adi !== iad) {
              PK.uyusmaz.push([o.text, iad, x.İl_Adi, x.İlce_Adi])
              continue
            }
            m[x.mahalleAdi] ??= {}
            m[x.mahalleAdi][x.posta_Kodu] = (m[x.mahalleAdi][x.posta_Kodu] || 0) + 1
          }
          il.ilceler[iad] = { kod: ik, satir, mahalle: m }
          ok = true
        } catch {
          await bekle(5000 * (d + 1))
        }
      }
      if (!ok) PK.hata.push([o.text, iad, ik])
      await bekle(800)
    }
  }

  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([JSON.stringify(PK)], { type: 'application/json' }))
  a.download = 'ptt-guncel.json'
  a.click()
})()
