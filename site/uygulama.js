(async function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const norm = (s) => String(s || "").toLocaleLowerCase("tr");

  const veri = await (await fetch("misafirhaneler.geojson", { cache: "no-cache" })).json();
  const tesisler = veri.features;

  const harita = L.map("harita").setView([39, 35], 6);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "© OpenStreetMap",
  }).addTo(harita);
  const kume = L.markerClusterGroup({ maxClusterRadius: 45 }).addTo(harita);

  const popup = (p) => `<b>${esc(p.tesisAdi)}</b><br>${esc(p.bakanlik)}<br>
    ${esc(p.il)}${p.ilce ? " / " + esc(p.ilce) : ""}<br>
    ${p.adres ? esc(p.adres) + "<br>" : ""}${p.telefon ? "☎ " + esc(p.telefon) + "<br>" : ""}
    ${p.konumKaynagi && p.konumKaynagi !== "adres" ? '<span style="opacity:.7">Konum yaklaşık (' + esc(p.konumKaynagi) + " merkezi)</span>" : ""}`;

  tesisler.forEach((f) => {
    f.ara = norm([f.properties.tesisAdi, f.properties.il, f.properties.ilce, f.properties.adres, f.properties.birim].join(" "));
    if (f.geometry) {
      const [x, y] = f.geometry.coordinates;
      f.isaret = L.marker([y, x]).bindPopup(popup(f.properties));
    }
  });

  const doldur = (sel, degerler) => [...new Set(degerler)].filter(Boolean).sort((a, b) => a.localeCompare(b, "tr"))
    .forEach((d) => sel.add(new Option(d, d)));
  doldur($("f-bakanlik"), tesisler.map((f) => f.properties.bakanlik));
  doldur($("f-il"), tesisler.map((f) => f.properties.il));

  $("s-toplam").textContent = tesisler.length.toLocaleString("tr");
  $("s-il").textContent = new Set(tesisler.map((f) => f.properties.il).filter(Boolean)).size;
  $("s-guncel").textContent = new Date(veri.guncelleme).toLocaleDateString("tr");

  function guncelle() {
    const q = norm($("f-ara").value.trim()), b = $("f-bakanlik").value, il = $("f-il").value;
    const gorunen = tesisler.filter((f) => (!b || f.properties.bakanlik === b) && (!il || f.properties.il === il) && (!q || f.ara.includes(q)));
    kume.clearLayers();
    kume.addLayers(gorunen.filter((f) => f.isaret).map((f) => f.isaret));
    $("s-gorunen").textContent = gorunen.length.toLocaleString("tr");
    $("liste").innerHTML = gorunen.slice(0, 500).map((f, i) => `<div class="tesis" data-i="${tesisler.indexOf(f)}">
      <h3>${esc(f.properties.tesisAdi)}</h3>
      <p class="soluk">${esc(f.properties.il)}${f.properties.ilce ? " / " + esc(f.properties.ilce) : ""} · ${esc(f.properties.bakanlik)}</p>
      ${f.properties.telefon ? `<p>☎ ${esc(f.properties.telefon)}</p>` : ""}</div>`).join("")
      + (gorunen.length > 500 ? '<p class="soluk" style="padding:10px 14px">İlk 500 sonuç gösteriliyor; filtreyi daraltın.</p>' : "");
    if ((b || il || q) && gorunen.some((f) => f.isaret)) {
      harita.fitBounds(L.latLngBounds(gorunen.filter((f) => f.isaret).map((f) => f.isaret.getLatLng())).pad(0.1), { maxZoom: 13 });
    }
  }
  $("liste").addEventListener("click", (e) => {
    const el = e.target.closest(".tesis");
    const f = el && tesisler[el.dataset.i];
    if (f && f.isaret) kume.zoomToShowLayer(f.isaret, () => f.isaret.openPopup());
  });
  ["f-ara", "f-bakanlik", "f-il"].forEach((id) => $(id).addEventListener("input", guncelle));
  guncelle();
})();
