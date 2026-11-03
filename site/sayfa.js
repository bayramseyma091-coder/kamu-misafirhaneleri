// Tesis, il ve iller sayfaları için küçük yardımcılar
(function () {
  const el = document.getElementById("mini-harita");
  if (el && window.L) {
    const harita = L.map(el, { scrollWheelZoom: false });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(harita);
    const ikon = (renk) => L.divIcon({ className: "", html: `<div class="isaret" style="--renk:${renk}"></div>`, iconSize: [26, 26], iconAnchor: [13, 30], popupAnchor: [0, -28] });
    if (el.dataset.noktalar) {
      const noktalar = JSON.parse(el.dataset.noktalar);
      const katman = L.featureGroup(noktalar.map(([y, x, renk, ad, sayfa]) => {
        const a = document.createElement("a");
        a.href = `../tesis/${sayfa}.html`;
        a.textContent = ad;
        return L.marker([y, x], { icon: ikon(renk), title: ad }).bindPopup(a);
      })).addTo(harita);
      if (noktalar.length) harita.fitBounds(katman.getBounds().pad(0.2), { maxZoom: 12 });
      else harita.setView([39, 35.2], 6);
    } else {
      const y = +el.dataset.y, x = +el.dataset.x;
      harita.setView([y, x], 12);
      L.marker([y, x], { icon: ikon(el.dataset.renk) }).addTo(harita);
    }
  }

  // Paylaş
  document.querySelectorAll("[data-paylas]").forEach((b) => b.addEventListener("click", async () => {
    const veri = { title: document.title, url: location.href };
    if (navigator.share) {
      try { await navigator.share(veri); } catch (_) { /* kullanıcı vazgeçti */ }
    } else {
      window.open("https://wa.me/?text=" + encodeURIComponent(document.title + " " + location.href), "_blank", "noopener");
    }
  }));

  // İl arama
  const ara = document.getElementById("il-ara");
  if (ara) {
    const norm = (s) => s.toLocaleLowerCase("tr").replace(/ı/g, "i").normalize("NFKD").replace(/[̀-ͯ]/g, "");
    ara.addEventListener("input", () => {
      const q = norm(ara.value.trim());
      document.querySelectorAll(".il-kart").forEach((k) => (k.hidden = q && !k.dataset.ad.includes(q)));
    });
  }
})();
