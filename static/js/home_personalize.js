(function initHomePersonalize() {
  'use strict';

  var root = document.getElementById('ivt-for-you');
  if (!root) return;

  var apiUrl = root.dataset.apiUrl || (document.body && document.body.dataset.profileApi) || '';
  if (!apiUrl) return;

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  function render(data) {
    if (!data || !data.personalized) {
      root.hidden = true;
      return;
    }

    var summaryEl = root.querySelector('[data-profile-summary]');
    if (summaryEl) summaryEl.textContent = data.summary || '';

    var destWrap = root.querySelector('[data-profile-dests]');
    if (destWrap && data.destinations && data.destinations.length) {
      destWrap.innerHTML = data.destinations.map(function (d) {
        var img = d.image
          ? '<img src="' + esc(d.image) + '" alt="" loading="lazy" width="400" height="260">'
          : '';
        return '<a class="dest-card dest-card--compact" href="' + esc(d.url) + '">'
          + img
          + '<span class="dest-card__name">' + esc(d.name) + '</span>'
          + (d.tagline ? '<span class="dest-card__tag">' + esc(d.tagline) + '</span>' : '')
          + '</a>';
      }).join('');
    }

    var itinWrap = root.querySelector('[data-profile-itins]');
    if (itinWrap && data.itineraries && data.itineraries.length) {
      itinWrap.innerHTML = data.itineraries.map(function (it) {
        return '<a class="tool-link-card" href="' + esc(it.url) + '">'
          + '<span class="tool-link-card__icon" aria-hidden="true">🗺️</span>'
          + '<span>' + esc(it.title) + (it.duration ? ' · ' + esc(it.duration) : '') + '</span>'
          + '</a>';
      }).join('');
    }

    var toolsWrap = root.querySelector('[data-profile-tools]');
    if (toolsWrap && data.tools && data.tools.length) {
      toolsWrap.innerHTML = data.tools.map(function (t) {
        return '<a class="tool-link-card" href="' + esc(t.url) + '">'
          + '<span class="tool-link-card__icon" aria-hidden="true">✦</span>'
          + '<span>' + esc(t.title) + '</span>'
          + '</a>';
      }).join('');
    }

    var prepareBtn = root.querySelector('[data-profile-prepare]');
    if (prepareBtn && data.prepare_url) prepareBtn.href = data.prepare_url;

    root.hidden = false;
  }

  function fetchRecos() {
    if (window.ivtProfile && !window.ivtProfile.enabled()) {
      root.hidden = true;
      return;
    }
    fetch(apiUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () { root.hidden = true; });
  }

  document.addEventListener('DOMContentLoaded', fetchRecos);
  window.addEventListener('ivt:profile-updated', fetchRecos);
  window.addEventListener('ivt:profile-cleared', function () { root.hidden = true; });
  window.addEventListener('ivt:consent-updated', fetchRecos);
})();

(function initContinueBar() {
  'use strict';

  var bar = document.getElementById('ivt-continue-bar');
  if (!bar) return;

  function refresh() {
    if (!window.ivtProfile || !window.ivtProfile.enabled()) {
      bar.hidden = true;
      return;
    }
    var p = window.ivtProfile.load();
    if (!p || !window.ivtProfile.hasSignal(p)) {
      bar.hidden = true;
      return;
    }
    var textEl = bar.querySelector('[data-continue-text]');
    var linkEl = bar.querySelector('[data-continue-link]');
    var lang = (document.documentElement.lang || 'fr').slice(0, 2);
    var preparePath = lang === 'en' ? '/en/plan-my-trip' : '/preparer-mon-voyage';
    if (p.c && p.c.length && linkEl) {
      var slug = p.c[0];
      linkEl.href = lang === 'en' ? '/en/' + slug : '/' + slug;
      if (textEl) {
        textEl.textContent = lang === 'en'
          ? 'Continue exploring ' + slug.replace(/-/g, ' ')
          : 'Continuez : ' + slug.replace(/-/g, ' ');
      }
    } else if (linkEl) {
      linkEl.href = preparePath;
    }
    bar.hidden = false;
  }

  document.addEventListener('DOMContentLoaded', refresh);
  window.addEventListener('ivt:profile-updated', refresh);
  window.addEventListener('ivt:profile-cleared', function () { bar.hidden = true; });
  window.addEventListener('ivt:consent-updated', refresh);
})();
