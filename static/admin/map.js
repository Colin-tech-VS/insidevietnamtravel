(function initAdminMap() {
  'use strict';

  var points = window.__MAP_ADMIN_POINTS__ || [];
  var el = document.getElementById('admin-map-preview');
  if (!el || typeof L === 'undefined') return;

  var map = L.map(el, { scrollWheelZoom: false }).setView([16.0, 108.0], 6);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  var bounds = [];
  var colors = { hotel: '#1B4D4A', activity: '#C4A053', food: '#C4654A', poi: '#3D6B5E' };

  points.forEach(function (p) {
    if (p.lat == null || p.lng == null) return;
    var c = colors[p.kind] || colors.poi;
    var marker = L.circleMarker([p.lat, p.lng], {
      radius: 8,
      color: '#fff',
      weight: 2,
      fillColor: c,
      fillOpacity: 0.9,
    }).addTo(map);
    marker.bindPopup('<strong>' + escapeHtml(p.title) + '</strong><br>' + escapeHtml(p.destination_name || p.destination_slug || ''));
    bounds.push([p.lat, p.lng]);
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 12 });
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

  function escapeHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
})();
