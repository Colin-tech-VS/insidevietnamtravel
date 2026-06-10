(function initAdminMap() {
  'use strict';

  var points = window.__MAP_ADMIN_POINTS__ || [];
  var kindMeta = window.__MAP_KIND_META__ || {};
  var el = document.getElementById('admin-map-preview');
  if (!el || typeof L === 'undefined') return;

  var fallback = { label: 'À voir', color: '#3D6B5E' };

  function metaFor(kind) {
    return kindMeta[kind] || kindMeta.poi || fallback;
  }

  var map = L.map(el, { scrollWheelZoom: false }).setView([16.0, 108.0], 6);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  var bounds = [];
  var kindsPresent = {};

  points.forEach(function (p) {
    if (p.lat == null || p.lng == null) return;
    var kind = p.kind || 'poi';
    kindsPresent[kind] = true;
    var marker = L.circleMarker([p.lat, p.lng], {
      radius: 8,
      color: '#fff',
      weight: 2,
      fillColor: metaFor(kind).color,
      fillOpacity: 0.9,
    }).addTo(map);
    marker.bindPopup('<strong>' + escapeHtml(p.title) + '</strong><br>' + escapeHtml(p.destination_name || p.destination_slug || ''));
    bounds.push([p.lat, p.lng]);
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 12 });
  }

  // Légende auto : un item par type présent sur la carte (ordre du serveur).
  var legendEl = document.getElementById('admin-map-legend');
  if (legendEl) {
    Object.keys(kindMeta).forEach(function (kind) {
      if (!kindsPresent[kind]) return;
      var item = document.createElement('span');
      item.className = 'admin-map-legend__item';
      var dot = document.createElement('i');
      dot.className = 'admin-map-legend__dot';
      dot.style.background = kindMeta[kind].color;
      item.appendChild(dot);
      item.appendChild(document.createTextNode(kindMeta[kind].label));
      legendEl.appendChild(item);
    });
    if (!legendEl.children.length) legendEl.hidden = true;
  }

  var provider = document.getElementById('map-provider');
  var customWrap = document.getElementById('map-custom-url-wrap');
  if (provider && customWrap) {
    function toggleCustom() {
      customWrap.hidden = provider.value !== 'custom';
    }
    provider.addEventListener('change', toggleCustom);
    toggleCustom();
  }

  var kindSelect = document.getElementById('map-kind');
  var kindCustomWrap = document.getElementById('map-kind-custom-wrap');
  if (kindSelect && kindCustomWrap) {
    function toggleKindCustom() {
      var isCustom = kindSelect.value === '__custom__';
      kindCustomWrap.hidden = !isCustom;
      var input = document.getElementById('map-kind-custom');
      if (input) input.required = isCustom;
    }
    kindSelect.addEventListener('change', toggleKindCustom);
    toggleKindCustom();
  }

  function escapeHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
})();
