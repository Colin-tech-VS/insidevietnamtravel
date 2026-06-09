(function initMaiChatMaps(global) {
  'use strict';

  var leafletPromise = null;
  var mapSeq = 0;

  var KIND_COLORS = {
    hotel: '#1B4D4A',
    activity: '#C4A053',
    food: '#C4654A',
    poi: '#3D6B5E',
    service: '#5B6B8C',
  };

  function loadLeaflet() {
    if (global.L) return Promise.resolve();
    if (leafletPromise) return leafletPromise;
    leafletPromise = new Promise(function (resolve, reject) {
      if (!document.querySelector('link[data-mai-leaflet]')) {
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        link.crossOrigin = 'anonymous';
        link.setAttribute('data-mai-leaflet', '1');
        document.head.appendChild(link);
      }
      if (document.querySelector('script[data-mai-leaflet]')) {
        var wait = 0;
        var t = setInterval(function () {
          wait += 1;
          if (global.L) { clearInterval(t); resolve(); }
          if (wait > 50) { clearInterval(t); reject(new Error('Leaflet timeout')); }
        }, 100);
        return;
      }
      var script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.crossOrigin = 'anonymous';
      script.defer = true;
      script.setAttribute('data-mai-leaflet', '1');
      script.onload = function () { resolve(); };
      script.onerror = function () { reject(new Error('Leaflet load failed')); };
      document.head.appendChild(script);
    });
    return leafletPromise;
  }

  function mountMap(el, points) {
    if (!el || !points || !points.length || !global.L) return;
    if (el.dataset.maiMapReady) return;
    el.dataset.maiMapReady = '1';
    el.innerHTML = '';

    var map = global.L.map(el, {
      scrollWheelZoom: false,
      dragging: true,
      zoomControl: false,
      attributionControl: true,
    }).setView([points[0].lat, points[0].lng], 13);

    global.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; OSM',
    }).addTo(map);

    var bounds = [];
    points.forEach(function (p) {
      if (p.lat == null || p.lng == null) return;
      var color = KIND_COLORS[p.kind] || KIND_COLORS.poi;
      var radius = p.highlight ? 10 : 7;
      global.L.circleMarker([p.lat, p.lng], {
        radius: radius,
        color: p.highlight ? '#fff' : color,
        weight: p.highlight ? 3 : 2,
        fillColor: color,
        fillOpacity: 0.95,
      }).addTo(map);
      bounds.push([p.lat, p.lng]);
    });

    if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [12, 12], maxZoom: 14 });
    }
    el._maiLeafletMap = map;
    setTimeout(function () { map.invalidateSize(); }, 120);
  }

  function invalidateIn(container) {
    if (!container || !global.L) return;
    container.querySelectorAll('.mai-chat__map-canvas[data-mai-map-ready]').forEach(function (el) {
      if (el._maiLeafletMap && el._maiLeafletMap.invalidateSize) {
        el._maiLeafletMap.invalidateSize();
      }
    });
  }

  function initIn(container) {
    if (!container) return;
    var maps = container.querySelectorAll('.mai-chat__map-canvas:not([data-mai-map-ready])');
    if (!maps.length) return;

    loadLeaflet().then(function () {
      maps.forEach(function (el) {
        var raw = el.getAttribute('data-points');
        if (!raw) return;
        try {
          mountMap(el, JSON.parse(raw));
        } catch (e) { /* ignore */ }
      });
    }).catch(function () {
      maps.forEach(function (el) {
        el.classList.add('mai-chat__map-canvas--error');
        el.textContent = el.getAttribute('data-error') || 'Map unavailable';
      });
    });
  }

  global.maiChatMaps = {
    nextId: function () {
      mapSeq += 1;
      return 'mai-map-' + mapSeq;
    },
    initIn: initIn,
    invalidateIn: invalidateIn,
  };
})(window);
