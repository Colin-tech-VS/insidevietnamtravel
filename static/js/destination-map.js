(function initDestinationMap() {
  'use strict';

  var root = document.getElementById('dest-map');
  if (!root) return;

  var apiUrl = root.dataset.apiUrl;
  var lang = root.dataset.lang || 'fr';
  var colors = { hotel: '#1B4D4A', activity: '#C4A053', food: '#C4654A', poi: '#3D6B5E', service: '#5B6B8C' };
  var emptyMsg = lang === 'en' ? 'Map loading…' : 'Chargement de la carte…';
  var leafletCss = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  var leafletJs = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  var leafletCssIntegrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
  var leafletJsIntegrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
  var started = false;

  root.innerHTML = '<p class="dest-map-empty">' + emptyMsg + '</p>';

  function loadStyle(href, integrity) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('link[data-leaflet-css]')) return resolve();
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.crossOrigin = '';
      link.setAttribute('data-leaflet-css', '1');
      if (integrity) link.integrity = integrity;
      link.onload = function () { resolve(); };
      link.onerror = reject;
      document.head.appendChild(link);
    });
  }

  function loadScript(src, integrity) {
    return new Promise(function (resolve, reject) {
      if (window.L) return resolve();
      var script = document.createElement('script');
      script.src = src;
      script.defer = true;
      script.crossOrigin = '';
      if (integrity) script.integrity = integrity;
      script.onload = function () { resolve(); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function whenVisible(el, cb) {
    if (!('IntersectionObserver' in window)) {
      cb();
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      observer.disconnect();
      cb();
    }, { rootMargin: '240px 0px', threshold: 0.01 });
    observer.observe(el);
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
    if (p.image) {
      html += '<img class="dest-map-popup__img" src="' + escapeHtml(p.image) + '" alt="' + escapeHtml(p.title) + '" loading="lazy">';
    }
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

  function renderMap(data) {
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
  }

  function boot() {
    if (started) return;
    started = true;
    Promise.all([
      loadStyle(leafletCss, leafletCssIntegrity),
      loadScript(leafletJs, leafletJsIntegrity),
    ])
      .then(function () {
        return fetch(apiUrl, { headers: { Accept: 'application/json' } });
      })
      .then(function (r) { return r.json(); })
      .then(renderMap)
      .catch(function () {
        root.innerHTML = '<p class="dest-map-empty">' + (lang === 'en' ? 'Unable to load map.' : 'Impossible de charger la carte.') + '</p>';
      });
  }

  whenVisible(root, boot);
})();
