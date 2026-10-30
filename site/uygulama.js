(async function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const norm = (s) => String(s || "").toLocaleLowerCase("tr");
  const telLink = (t) => "tel:" + String(t).split(/[\/(]/)[0].replace(/[^\d+]/g, "");
  const TEL_IKON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>';

  // Bakanlık renkleri
  const RENKLER = {
    "Millî Eğitim Bakanlığı": "#2563eb",
    "İçişleri Bakanlığı": "#dc2626",
    "Millî Savunma Bakanlığı": "#4d7c0f",
    "Kültür ve Turizm Bakanlığı": "#9333ea",
    "Sağlık Bakanlığı": "#0891b2",
  };
  const YEDEK = ["#db2777", "#ea580c", "#0d9488", "#7c3aed", "#65a30d"];
  const renk = (b) => RENKLER[b] || (RENKLER[b] = YEDEK[Object.keys(RENKLER).length % YEDEK.length]);
  const kisaAd = (b) => b.replace(/ Bakanlığı$/, "");

  const [veri, olaylar] = await Promise.all([
    fetch("misafirhaneler.geojson", { cache: "no-cache" }).then((r) => r.json()),
    fetch("degisiklikler.json", { cache: "no-cache" }).then((r) => r.json()).catch(() => []),
  ]);
  const tesisler = veri.features;

  // Harita
  const karanlik = matchMedia("(prefers-color-scheme: dark)").matches;
  const harita = L.map("harita", { zoomControl: true, scrollWheelZoom: true }).setView([39, 35.2], 6);
  L.tileLayer(`https://{s}.basemaps.cartocdn.com/${karanlik ? "dark_all" : "light_all"}/{z}/{x}/{y}{r}.png`, {
    maxZoom: 19, subdomains: "abcd",
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>',
  }).addTo(harita);
  const kume = L.markerClusterGroup({
    maxClusterRadius: 48, showCoverageOnHover: false,
    iconCreateFunction: (c) => {
      const n = c.getChildCount(), b = n < 10 ? 34 : n < 50 ? 42 : 50;
      return L.divIcon({ html: `<div class="kume" style="width:${b}px;height:${b}px">${n}</div>`, className: "", iconSize: [b, b] });
    },
  }).addTo(harita);

  const popup = (p) => `<div style="--renk:${renk(p.bakanlik)}">
    <span class="bakanlik"><i></i>${esc(p.bakanlik)}</span>
    <h3>${esc(p.tesisAdi)}</h3>
    <p class="soluk">${esc(p.il)}${p.ilce ? " / " + esc(p.ilce) : ""}</p>
    ${p.adres ? `<p>${esc(p.adres)}</p>` : ""}
    ${p.telefon ? `<p><a class="tel" href="${telLink(p.telefon)}">${TEL_IKON}${esc(p.telefon)}</a></p>` : ""}
    ${p.konumKaynagi && p.konumKaynagi !== "adres" ? `<p class="not">Konum yaklaşık (${p.konumKaynagi === "il" ? "il" : "ilçe"} merkezi)</p>` : ""}
  </div>`;

  tesisler.forEach((f, i) => {
    const p = f.properties;
    f.i = i;
    f.ara = norm([p.tesisAdi, p.il, p.ilce, p.adres, p.birim].join(" "));
    if (f.geometry) {
      const [x, y] = f.geometry.coordinates;
      f.isaret = L.marker([y, x], {
        icon: L.divIcon({ className: "", html: `<div class="isaret" style="--renk:${renk(p.bakanlik)}"></div>`, iconSize: [26, 26], iconAnchor: [13, 30], popupAnchor: [0, -28] }),
        title: p.tesisAdi,
      }).bindPopup(popup(p));
    }
  });

  // Filtreler
  const sayac = {};
  tesisler.forEach((f) => (sayac[f.properties.bakanlik] = (sayac[f.properties.bakanlik] || 0) + 1));
  const secili = new Set();
  Object.entries(sayac).sort((a, b) => b[1] - a[1]).forEach(([b, n]) => {
    const btn = document.createElement("button");
    btn.className = "cip";
    btn.type = "button";
    btn.style.setProperty("--renk", renk(b));
    btn.setAttribute("aria-pressed", "false");
    btn.innerHTML = `<i></i>${esc(kisaAd(b))} <b>${n}</b>`;
    btn.addEventListener("click", () => {
      secili.has(b) ? secili.delete(b) : secili.add(b);
      btn.setAttribute("aria-pressed", secili.has(b));
      guncelle(true);
    });
    $("f-bakanlik").append(btn);
  });
  [...new Set(tesisler.map((f) => f.properties.il))].filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "tr")).forEach((il) => $("f-il").add(new Option(il, il)));

  $("s-toplam").textContent = tesisler.length.toLocaleString("tr");
  $("s-il").textContent = new Set(tesisler.map((f) => f.properties.il).filter(Boolean)).size;
  $("s-guncel").textContent = new Date(veri.guncelleme).toLocaleDateString("tr", { day: "numeric", month: "short", year: "numeric" });

  const kart = (f) => {
    const p = f.properties;
    return `<button class="tesis" data-i="${f.i}" style="--renk:${renk(p.bakanlik)}">
      <h3>${esc(p.tesisAdi)}</h3>
      <p class="yer">${esc(p.il)}${p.ilce ? " / " + esc(p.ilce) : ""}</p>
      <div class="alt"><span class="etiket">${esc(kisaAd(p.bakanlik))}</span>
      ${p.telefon ? `<a class="tel" href="${telLink(p.telefon)}">${TEL_IKON}${esc(p.telefon)}</a>` : ""}</div>
    </button>`;
  };

  let zamanlayici;
  function guncelle(sigdir) {
    const q = norm($("f-ara").value.trim()), il = $("f-il").value;
    const gorunen = tesisler.filter((f) =>
      (!secili.size || secili.has(f.properties.bakanlik)) && (!il || f.properties.il === il) && (!q || f.ara.includes(q)));
    const isaretler = gorunen.filter((f) => f.isaret).map((f) => f.isaret);
    kume.clearLayers();
    kume.addLayers(isaretler);
    $("s-gorunen").textContent = gorunen.length.toLocaleString("tr");
    $("liste-sayi").textContent = `${gorunen.length.toLocaleString("tr")} sonuç`;
    $("liste").innerHTML = gorunen.length
      ? gorunen.slice(0, 400).map(kart).join("") +
        (gorunen.length > 400 ? '<p class="bos">İlk 400 sonuç gösteriliyor. Aramayı daraltın.</p>' : "")
      : '<p class="bos">Bu filtreye uyan tesis bulunamadı.</p>';
    if (sigdir && isaretler.length) {
      harita.fitBounds(L.latLngBounds(isaretler.map((m) => m.getLatLng())).pad(0.15), { maxZoom: 12 });
    }
  }
  $("f-ara").addEventListener("input", () => { clearTimeout(zamanlayici); zamanlayici = setTimeout(() => guncelle(true), 200); });
  $("f-il").addEventListener("change", () => guncelle(true));

  $("liste").addEventListener("click", (e) => {
    if (e.target.closest(".tel")) return;
    const el = e.target.closest(".tesis");
    const f = el && tesisler[el.dataset.i];
    if (!f || !f.isaret) return;
    gorunumSec("harita");
    kume.zoomToShowLayer(f.isaret, () => f.isaret.openPopup());
  });

  // Mobil sekmeler
  function gorunumSec(g) {
    $("duzen").dataset.gorunum = g;
    document.querySelectorAll(".sekme button").forEach((b) => b.setAttribute("aria-selected", b.dataset.gorunum === g));
    if (g === "harita") setTimeout(() => harita.invalidateSize(), 0);
  }
  document.querySelectorAll(".sekme button").forEach((b) => b.addEventListener("click", () => gorunumSec(b.dataset.gorunum)));

  // Son değişiklikler
  const ETIKET = { yeni: "Yeni açıldı", guncellendi: "Güncellendi", kapandi: "Kapandı" };
  $("son-olaylar").innerHTML = olaylar.length
    ? olaylar.slice(0, 5).map((o) => `<article class="olay olay-${o.tur}">
        <div class="olay-ust"><span class="rozet">${ETIKET[o.tur]}</span>
        <time datetime="${o.tarih}">${new Date(o.tarih).toLocaleDateString("tr", { day: "numeric", month: "long", year: "numeric" })}</time></div>
        <h3>${esc(o.tesis.tesisAdi)}</h3>
        <p class="soluk">${esc(o.tesis.il)}${o.tesis.ilce ? " / " + esc(o.tesis.ilce) : ""} · ${esc(o.tesis.bakanlik)}</p>
      </article>`).join("")
    : '<div class="bos-kart">Henüz değişiklik yok. Bir tesis açıldığında, kapandığında ya da bilgisi değiştiğinde burada görünecek.</div>';
  if (!olaylar.length) $("son-olaylar").classList.remove("zaman");

  guncelle(false);
})();
