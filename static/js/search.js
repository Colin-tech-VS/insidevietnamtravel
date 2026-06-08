(function () {
  var overlay = document.getElementById('search-overlay');
  var input = document.getElementById('search-input');
  var resultsEl = document.getElementById('search-results');
  var hintEl = document.getElementById('search-hint');
  if (!overlay || !input || !resultsEl) return;

  var openers = document.querySelectorAll('[data-search-open]');
  var closers = overlay.querySelectorAll('[data-search-close]');
  var index = null;
  var loading = false;
  var lastFocus = null;

  var GROUPS = ['destination', 'hotel', 'activity', 'itinerary', 'article', 'tool'];
  var groupLabel = {
    destination: overlay.dataset.groupDestination,
    hotel: overlay.dataset.groupHotel,
    activity: overlay.dataset.groupActivity,
    itinerary: overlay.dataset.groupItinerary,
    article: overlay.dataset.groupArticle,
    tool: overlay.dataset.groupTool,
  };

  function normalize(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function loadIndex() {
    if (index || loading) return;
    loading = true;
    fetch(overlay.dataset.indexUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) { index = data; loading = false; if (input.value) render(input.value); })
      .catch(function () { loading = false; });
  }

  function open() {
    lastFocus = document.activeElement;
    overlay.hidden = false;
    document.body.style.overflow = 'hidden';
    loadIndex();
    setTimeout(function () { input.focus(); }, 30);
  }

  function close() {
    overlay.hidden = true;
    document.body.style.overflow = '';
    input.value = '';
    resultsEl.innerHTML = '';
    if (hintEl) hintEl.style.display = '';
    if (lastFocus) lastFocus.focus();
  }

  function esc(s) {
    return (s || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function render(query) {
    var q = normalize(query.trim());
    if (hintEl) hintEl.style.display = q ? 'none' : '';
    if (!q) { resultsEl.innerHTML = ''; return; }
    if (!index) { resultsEl.innerHTML = ''; return; }

    var matches = index.filter(function (item) {
      return normalize(item.t).indexOf(q) !== -1 || normalize(item.s).indexOf(q) !== -1;
    });

    if (!matches.length) {
      resultsEl.innerHTML = '<p class="search-results__empty">' + esc(overlay.dataset.empty) + '</p>';
      return;
    }

    var html = '';
    GROUPS.forEach(function (g) {
      var group = matches.filter(function (m) { return m.g === g; }).slice(0, 6);
      if (!group.length) return;
      html += '<div class="search-group"><p class="search-group__label">' + esc(groupLabel[g]) + '</p>';
      group.forEach(function (m) {
        // Les hôtels et activités sont des liens affiliés (m.x) : nouvel onglet + rel.
        var attrs = m.x
          ? ' target="_blank" rel="sponsored nofollow noopener"'
          : '';
        var badge = m.x ? '<span class="search-result__ext" aria-hidden="true">↗</span>' : '';
        html += '<a class="search-result' + (m.x ? ' search-result--affiliate' : '') + '" href="' + esc(m.u) + '"' + attrs + '>' +
          '<span class="search-result__title">' + esc(m.t) + badge + '</span>' +
          (m.s ? '<span class="search-result__sub">' + esc(m.s) + '</span>' : '') +
          '</a>';
      });
      html += '</div>';
    });
    resultsEl.innerHTML = html;
  }

  openers.forEach(function (b) { b.addEventListener('click', open); });
  closers.forEach(function (b) { b.addEventListener('click', close); });
  overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
  input.addEventListener('input', function () { render(input.value); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !overlay.hidden) close();
    if ((e.key === '/' || (e.key === 'k' && (e.metaKey || e.ctrlKey))) && overlay.hidden) {
      var tag = (document.activeElement.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      e.preventDefault();
      open();
    }
  });
})();
