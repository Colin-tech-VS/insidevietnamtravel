(function initDestinationMap() {
  'use strict';

  var root = document.getElementById('dest-map');
  if (!root) return;

  var apiUrl = root.dataset.apiUrl;
  var lang = root.dataset.lang || 'fr';
  var colors = { hotel: '#1B4D4A', activity: '#C4A053', food: '#C4654A', poi: '#3D6B5E', service: '#5B6B8C' };
  var emptyMsg = lang === 'en'
    ? 'Map loading…'
    : 'Chargement de la carte…';

  root.innerHTML = '<p class="dest-map-empty">' + emptyMsg + '</p>';

  function waitLeaflet(cb) {
    if (window.L) return cb();
    var n = 0;
    var t = setInterval(function () {
      n += 1;
      if (window.L || n > 40) {
        clearInterval(t);
        if (window.L) cb();
      }
    }, 100);
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderLegend(legend) {
    if (!legend || !legend.length) return;
    var box = document.getElementById('dest-map-legend');
    if (!box) return;
    box.innerHTML = '';
    legend.forEach(function (entry) {
      var item = document.createElement('span');
      item.className = 'dest-map-legend__item';
      item.style.setProperty('--legend-dot', entry.color || colors.poi);
      item.textContent = entry.label || entry.kind;
      box.appendChild(item);
    });
  }

  function popupHtml(p) {
    var html = '<div class="dest-map-popup">';
    html += '<strong>' + escapeHtml(p.title) + '</strong>';
    if (p.kind_label) html += '<span class="dest-map-popup__kind">' + escapeHtml(p.kind_label) + '</span>';
    if (p.desc) html += '<p>' + escapeHtml(p.desc) + '</p>';
    if (p.price_hint) html += '<p class="dest-map-popup__price">' + escapeHtml(p.price_hint) + '</p>';
    if (p.affiliate_url) {
      html += '<a class="dest-map-popup__cta" href="' + escapeHtml(p.affiliate_url) + '" target="_blank" rel="sponsored noopener noreferrer">'
        + escapeHtml(p.affiliate_cta || (lang === 'en' ? 'Book' : 'Réserver')) + ' ↗</a>';
    }
    html += '</div>';
    return html;
  }

  fetch(apiUrl, { headers: { Accept: 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      waitLeaflet(function () {
        root.innerHTML = '';
        var points = (data && data.points) || [];
        if (!points.length) {
          root.innerHTML = '<p class="dest-map-empty">' + (lang === 'en' ? 'Map coming soon for this city.' : 'Carte bientôt disponible pour cette ville.') + '</p>';
          return;
        }

        var map = L.map(root, { scrollWheelZoom: false }).setView([points[0].lat, points[0].lng], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 18,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
        }).addTo(map);

        renderLegend(data.legend);

        var bounds = [];
        points.forEach(function (p) {
          if (p.lat == null || p.lng == null) return;
          var c = p.color || colors[p.kind] || colors.poi;
          var marker = L.circleMarker([p.lat, p.lng], {
            radius: 9,
            color: '#fff',
            weight: 2,
            fillColor: c,
            fillOpacity: 0.92,
          }).addTo(map);
          marker.bindPopup(popupHtml(p), { maxWidth: 280 });
          bounds.push([p.lat, p.lng]);
        });

        if (bounds.length > 1) {
          map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 });
        }
        setTimeout(function () { map.invalidateSize(); }, 200);
      });
    })
    .catch(function () {
      root.innerHTML = '<p class="dest-map-empty">' + (lang === 'en' ? 'Unable to load map.' : 'Impossible de charger la carte.') + '</p>';
    });
})();
