(function initMaiChat() {
  'use strict';

  var root = document.getElementById('mai-chat');
  if (!root) return;

  var fab = document.getElementById('mai-chat-fab');
  var fabLabel = document.getElementById('mai-chat-fab-label');
  var panel = document.getElementById('mai-chat-panel');
  var backdrop = document.getElementById('mai-chat-backdrop');
  var closeBtn = document.getElementById('mai-chat-close');
  var resizeHandle = document.getElementById('mai-chat-resize');
  var messagesEl = document.getElementById('mai-chat-messages');
  var suggestionsEl = document.getElementById('mai-chat-suggestions');
  var form = document.getElementById('mai-chat-form');
  var input = document.getElementById('mai-chat-input');
  var apiUrl = root.dataset.apiUrl;
  var lang = root.dataset.lang || 'fr';
  var history = [];
  var seenPhotos = []; // URLs déjà affichées — renvoyées au serveur pour ne jamais répéter une image
  var busy = false;
  var opened = false;

  var i18n = {
    typing: root.dataset.typing || '…',
    error: root.dataset.error || 'Error',
    affiliate: root.dataset.affiliateBadge || 'Partner',
    linksSite: root.dataset.linksSite || (lang === 'en' ? 'Read on the site' : 'À lire sur le site'),
    linksPartner: root.dataset.linksPartner || (lang === 'en' ? 'Partner picks' : 'Bons plans partenaires'),
    greeting: root.dataset.greeting || '',
    mapSubtitle: root.dataset.mapSubtitle || 'Interactive map',
    mapCta: root.dataset.mapCta || 'View full map',
    mapOn: root.dataset.mapOn || 'On the map',
    mapError: root.dataset.mapError || 'Map unavailable',
    resizeReset: root.dataset.resizeReset || 'Size reset',
  };

  var SIZE_KEY = 'ivt_mai_chat_size';
  var SIZE_MIN_W = 280;
  var SIZE_MIN_H = 320;
  var SIZE_DEFAULT_W = 360;
  var SIZE_DEFAULT_H = 520;
  var resizeActive = false;
  var resizeStartX = 0;
  var resizeStartY = 0;
  var resizeStartW = 0;
  var resizeStartH = 0;

  function clamp(n, min, max) {
    return Math.min(max, Math.max(min, n));
  }

  function sizeLimits() {
    var pad = 48;
    return {
      maxW: Math.max(SIZE_MIN_W, Math.min(560, window.innerWidth - pad)),
      maxH: Math.max(SIZE_MIN_H, Math.min(720, window.innerHeight - pad)),
    };
  }

  function resizeEnabled() {
    return window.matchMedia('(min-width: 481px)').matches;
  }

  function applyChatSize(w, h, persist) {
    if (!resizeEnabled()) return;
    var limits = sizeLimits();
    w = Math.round(clamp(w, SIZE_MIN_W, limits.maxW));
    h = Math.round(clamp(h, SIZE_MIN_H, limits.maxH));
    root.style.setProperty('--mai-panel-w', w + 'px');
    root.style.setProperty('--mai-panel-h', h + 'px');
    root.classList.add('mai-chat--custom-size');
    if (persist) {
      try {
        localStorage.setItem(SIZE_KEY, JSON.stringify({ w: w, h: h }));
      } catch (e) { /* ignore */ }
    }
  }

  function resetChatSize() {
    root.classList.remove('mai-chat--custom-size');
    root.style.removeProperty('--mai-panel-w');
    root.style.removeProperty('--mai-panel-h');
    try {
      localStorage.removeItem(SIZE_KEY);
    } catch (e) { /* ignore */ }
    invalidateChatMaps();
  }

  function loadSavedChatSize() {
    if (!resizeEnabled()) return;
    try {
      var raw = localStorage.getItem(SIZE_KEY);
      if (!raw) return;
      var saved = JSON.parse(raw);
      if (saved && saved.w && saved.h) {
        applyChatSize(saved.w, saved.h, false);
      }
    } catch (e) { /* ignore */ }
  }

  function invalidateChatMaps() {
    if (!window.maiChatMaps || !messagesEl) return;
    window.requestAnimationFrame(function () {
      if (window.maiChatMaps.invalidateIn) {
        window.maiChatMaps.invalidateIn(messagesEl);
      }
    });
  }

  function onResizeMove(clientX, clientY) {
    var dw = resizeStartX - clientX;
    var dh = resizeStartY - clientY;
    applyChatSize(resizeStartW + dw, resizeStartH + dh, false);
  }

  function stopResize() {
    if (!resizeActive) return;
    resizeActive = false;
    document.body.classList.remove('mai-chat-resizing');
    document.removeEventListener('mousemove', onResizeMouseMove);
    document.removeEventListener('mouseup', stopResize);
    document.removeEventListener('touchmove', onResizeTouchMove);
    document.removeEventListener('touchend', stopResize);
    document.removeEventListener('touchcancel', stopResize);
    var rect = panel.getBoundingClientRect();
    applyChatSize(rect.width, rect.height, true);
    invalidateChatMaps();
  }

  function onResizeMouseMove(e) {
    if (!resizeActive) return;
    e.preventDefault();
    onResizeMove(e.clientX, e.clientY);
  }

  function onResizeTouchMove(e) {
    if (!resizeActive || !e.touches.length) return;
    e.preventDefault();
    onResizeMove(e.touches[0].clientX, e.touches[0].clientY);
  }

  function startResize(clientX, clientY) {
    if (!resizeEnabled() || !resizeHandle) return;
    var rect = panel.getBoundingClientRect();
    resizeActive = true;
    resizeStartX = clientX;
    resizeStartY = clientY;
    resizeStartW = rect.width;
    resizeStartH = rect.height;
    root.classList.add('mai-chat--custom-size');
    document.body.classList.add('mai-chat-resizing');
    document.addEventListener('mousemove', onResizeMouseMove);
    document.addEventListener('mouseup', stopResize);
    document.addEventListener('touchmove', onResizeTouchMove, { passive: false });
    document.addEventListener('touchend', stopResize);
    document.addEventListener('touchcancel', stopResize);
  }

  function initChatResize() {
    if (!resizeHandle) return;
    loadSavedChatSize();

    resizeHandle.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      startResize(e.clientX, e.clientY);
    });

    resizeHandle.addEventListener('touchstart', function (e) {
      if (!e.touches.length) return;
      e.stopPropagation();
      startResize(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });

    resizeHandle.addEventListener('dblclick', function (e) {
      e.preventDefault();
      e.stopPropagation();
      resetChatSize();
    });

    window.addEventListener('resize', function () {
      if (!root.classList.contains('mai-chat--custom-size')) return;
      if (!resizeEnabled()) {
        resetChatSize();
        return;
      }
      var rect = panel.getBoundingClientRect();
      applyChatSize(rect.width, rect.height, true);
      invalidateChatMaps();
    });
  }

  initChatResize();

  var suggestions = [];
  try {
    suggestions = JSON.parse(root.dataset.suggestions || '[]');
  } catch (e) {
    suggestions = [];
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function applyEmphasis(html, streaming) {
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="mai-chat__emph">$1</strong>');
    if (streaming) {
      html = html.replace(/\*\*([^*]*)$/, '$1');
    }
    return html;
  }

  function urlDomain(url) {
    var m = /^https?:\/\/([^/?#]+)/i.exec(String(url || ''));
    var host = m ? m[1] : String(url || '');
    return host.replace(/^www\./i, '').split(':')[0];
  }

  var BRANDS = [
    ['booking.', { icon: '🏨', cls: 'hotel', name: 'Booking.com' }],
    ['agoda.', { icon: '🏨', cls: 'hotel', name: 'Agoda' }],
    ['getyourguide', { icon: '🎟️', cls: 'activity', name: 'GetYourGuide' }],
    ['viator.', { icon: '🎟️', cls: 'activity', name: 'Viator' }],
    ['klook.', { icon: '🎟️', cls: 'activity', name: 'Klook' }],
    ['airalo.', { icon: '📶', cls: 'esim', name: 'Airalo' }],
    ['holafly', { icon: '📶', cls: 'esim', name: 'Holafly' }],
    ['heymondo', { icon: '🛡️', cls: 'insurance', name: 'Heymondo' }],
    ['12go.', { icon: '🚌', cls: 'transport', name: '12Go' }],
  ];

  function brandFor(url) {
    var host = urlDomain(url).toLowerCase();
    for (var i = 0; i < BRANDS.length; i++) {
      if (host.indexOf(BRANDS[i][0]) !== -1) return BRANDS[i][1];
    }
    var here = (window.location.hostname || '').replace(/^www\./i, '');
    if (here && host === here) return { icon: '📖', cls: 'site', name: host };
    return { icon: '🔗', cls: 'ext', name: host };
  }

  function inlineLinkChip(url) {
    var brand = brandFor(url);
    return '<a class="mai-chat__inline-link" href="' + url + '" target="_blank" rel="noopener">'
      + '<span class="mai-chat__inline-link-ico" aria-hidden="true">' + brand.icon + '</span>'
      + '<span class="mai-chat__inline-link-text">' + brand.name + '</span>'
      + '<span class="mai-chat__inline-link-arrow" aria-hidden="true">↗</span></a>';
  }

  function formatMessage(text, streaming) {
    var raw = String(text || '');
    raw = raw.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    raw = raw.replace(/<\s*(https?:\/\/[^>]+)\s*>/g, '$1');
    raw = raw.replace(/\bhttps?:\/\/[^\s\]\)<>«»;,]+/g, '');
    raw = raw.replace(/\b(?:www\.)?[a-z0-9][-a-z0-9]*\.(?:gov(?:t)?\.vn|go\.vn|gov\.vn)[^\s,;]*/gi, '');
    raw = raw.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
    var escaped = escapeHtml(raw);
    escaped = applyEmphasis(escaped, !!streaming);
    var blocks = escaped.split(/\n{2,}/);
    if (blocks.length === 1) {
      return blocks[0].replace(/\n/g, '<br>');
    }
    var html = '';
    blocks.forEach(function (block) {
      block = block.replace(/\n/g, '<br>').trim();
      if (!block) return;
      html += '<p class="mai-chat__p">' + block + '</p>';
    });
    return html || escaped.replace(/\n/g, '<br>');
  }

  var scrollRaf = 0;
  function scrollBottom() {
    if (scrollRaf) return;
    scrollRaf = window.requestAnimationFrame(function () {
      scrollRaf = 0;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function createAssistantRow(extraClass) {
    var wrap = document.createElement('div');
    wrap.className = 'mai-chat__row mai-chat__row--assistant' + (extraClass ? ' ' + extraClass : '');
    var av = document.createElement('span');
    av.className = 'mai-chat__row-avatar';
    av.setAttribute('aria-hidden', 'true');
    av.textContent = '🌸';
    var body = document.createElement('div');
    body.className = 'mai-chat__row-body';
    wrap.appendChild(av);
    wrap.appendChild(body);
    messagesEl.appendChild(wrap);
    scrollBottom();
    return { wrap: wrap, body: body };
  }

  function appendBubble(role, html, extraClass) {
    if (role === 'assistant') {
      var row = createAssistantRow(extraClass);
      var bubble = document.createElement('div');
      bubble.className = 'mai-chat__bubble mai-chat__bubble--assistant';
      bubble.innerHTML = html;
      row.body.appendChild(bubble);
      return row.wrap;
    }
    var wrap = document.createElement('div');
    wrap.className = 'mai-chat__bubble-wrap mai-chat__bubble-wrap--user' + (extraClass ? ' ' + extraClass : '');
    var bubble = document.createElement('div');
    bubble.className = 'mai-chat__bubble mai-chat__bubble--user';
    bubble.innerHTML = html;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function renderPhotos(photos) {
    if (!photos || !photos.length) return '';
    var html = '<div class="mai-chat__photos">';
    photos.forEach(function (p) {
      html += '<figure class="mai-chat__photo">';
      if (p.page_url) {
        html += '<a class="mai-chat__photo-link" href="' + escapeHtml(p.page_url) + '" target="_blank" rel="noopener">';
      }
      html += '<img class="mai-chat__photo-img" src="' + escapeHtml(p.url) + '" alt="' + escapeHtml(p.alt || '') + '" loading="lazy" decoding="async">';
      if (p.page_url) html += '</a>';
      if (p.caption || p.credit) {
        html += '<figcaption class="mai-chat__photo-cap">';
        if (p.caption) html += '<span>' + escapeHtml(p.caption) + '</span>';
        if (p.credit) html += ' <span class="mai-chat__photo-credit">' + escapeHtml(p.credit) + '</span>';
        html += '</figcaption>';
      }
      html += '</figure>';
    });
    html += '</div>';
    return html;
  }

  function renderRefLink(url, label, isAff) {
    return '<a class="mai-chat__ref' + (isAff ? ' mai-chat__ref--aff' : '') + '" href="' + escapeHtml(url) + '" target="_blank" rel="' + (isAff ? 'noopener sponsored' : 'noopener') + '">'
      + escapeHtml(label) + '</a>';
  }

  function renderLinks(siteLinks, affiliateLinks, mapCards) {
    var refs = [];
    (siteLinks || []).slice(0, 1).forEach(function (l) {
      refs.push(renderRefLink(l.url, l.title, false));
    });
    (affiliateLinks || []).slice(0, 1).forEach(function (l) {
      refs.push(renderRefLink(l.url, l.label, true));
    });
    (mapCards || []).slice(0, 1).forEach(function (card) {
      if (card.map_url) {
        refs.push(renderRefLink(card.map_url, (card.name || '') + ' — ' + i18n.mapCta, false));
      }
    });
    if (!refs.length) return '';
    return '<div class="mai-chat__refs">' + refs.join('') + '</div>';
  }

  function showTyping() {
    var row = createAssistantRow('mai-chat__row--typing');
    row.body.innerHTML = '<div class="mai-chat__bubble mai-chat__bubble--assistant mai-chat__bubble--typing">'
      + '<span class="mai-chat__typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>'
      + '</div>';
    row.wrap.dataset.typing = '1';
    return row.wrap;
  }

  var supportsUnicodeProps = (function () {
    try {
      return /\p{Extended_Pictographic}/u.test('🌸');
    } catch (e) {
      return false;
    }
  }());

  function isEmojiChar(ch) {
    if (supportsUnicodeProps) {
      return /\p{Extended_Pictographic}/u.test(ch);
    }
    var code = ch.codePointAt(0) || 0;
    return code > 0xFFFF;
  }

  function buildStreamUnits(text) {
    return Array.from(String(text || ''));
  }

  function unitPause(unit, progress) {
    if (/\s/.test(unit)) return 3;
    if (/[.!?…]/.test(unit)) return 14;
    if (/[,;:]/.test(unit)) return 8;
    if (isEmojiChar(unit)) return 12;
    var ms = 7;
    if (progress > 0.5) ms *= 0.75;
    if (progress > 0.8) ms *= 0.65;
    return ms;
  }

  function streamAssistantMessage(text, linksHtml, photosHtml) {
    return new Promise(function (resolve) {
      removeTyping();

      var row = createAssistantRow('mai-chat__row--streaming');
      var bubble = document.createElement('div');
      bubble.className = 'mai-chat__bubble mai-chat__bubble--assistant mai-chat__bubble--streaming';
      bubble.innerHTML = '<div class="mai-chat__stream">'
        + '<span class="mai-chat__stream-text"></span>'
        + '<span class="mai-chat__cursor" aria-hidden="true"></span>'
        + '</div>';
      row.body.appendChild(bubble);

      var textEl = bubble.querySelector('.mai-chat__stream-text');
      var units = buildStreamUnits(text);
      var unitIndex = 0;
      var acc = '';
      var done = false;
      var rafId = 0;
      var carryMs = 0;
      var lastTs = 0;

      function revealExtras() {
        if (photosHtml) {
          var ph = document.createElement('div');
          ph.innerHTML = photosHtml.trim();
          if (ph.firstElementChild) row.body.appendChild(ph.firstElementChild);
        }
        if (linksHtml) {
          var holder = document.createElement('div');
          holder.innerHTML = linksHtml.trim();
          if (holder.firstElementChild) row.body.appendChild(holder.firstElementChild);
        }
        scrollBottom();
      }

      function finishInstant() {
        if (done) return;
        done = true;
        if (rafId) window.cancelAnimationFrame(rafId);
        textEl.innerHTML = formatMessage(text, false);
        var cursor = bubble.querySelector('.mai-chat__cursor');
        if (cursor) cursor.remove();
        bubble.classList.remove('mai-chat__bubble--streaming');
        row.wrap.classList.remove('mai-chat__row--streaming');
        revealExtras();
        scrollBottom();
        resolve();
      }

      function tick(ts) {
        if (done) return;
        try {
          if (!lastTs) lastTs = ts;
          carryMs += ts - lastTs;
          lastTs = ts;

          while (unitIndex < units.length) {
            var pause = unitPause(units[unitIndex], unitIndex / Math.max(units.length, 1));
            if (carryMs < pause) break;
            carryMs -= pause;
            acc += units[unitIndex];
            unitIndex += 1;
            textEl.innerHTML = formatMessage(acc, true);
          }
          scrollBottom();

          if (unitIndex >= units.length) {
            finishInstant();
            return;
          }
          rafId = window.requestAnimationFrame(tick);
        } catch (err) {
          finishInstant();
        }
      }

      rafId = window.requestAnimationFrame(tick);
    });
  }

  function removeTyping() {
    var el = messagesEl.querySelector('[data-typing="1"]');
    if (el) el.remove();
  }

  function renderSuggestions() {
    if (!suggestionsEl || !suggestions.length) return;
    suggestionsEl.innerHTML = '';
    suggestions.forEach(function (q) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mai-chat__chip';
      btn.textContent = q;
      btn.addEventListener('click', function () {
        input.value = q;
        form.requestSubmit();
      });
      suggestionsEl.appendChild(btn);
    });
  }

  function hideSuggestions() {
    if (suggestionsEl) suggestionsEl.innerHTML = '';
  }

  var openLabel = root.dataset.open || 'Chat';
  var closeLabel = root.dataset.close || 'Close';

  function isOpen() {
    return !panel.hidden;
  }

  function loadDynamicSuggestions() {
    var api = document.body.dataset.profileApi;
    if (!window.ivtProfile || !window.ivtProfile.enabled() || !api) return;
    fetch(api, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.suggestions && data.suggestions.length) {
          suggestions = data.suggestions;
          if (opened && !busy) renderSuggestions();
        }
      })
      .catch(function () {});
  }

  function openPanel() {
    panel.hidden = false;
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.setAttribute('aria-hidden', 'false');
    }
    fab.setAttribute('aria-expanded', 'true');
    fab.setAttribute('aria-label', closeLabel);
    if (fabLabel) fabLabel.textContent = closeLabel;
    document.body.classList.add('mai-chat-open');
    if (!opened) {
      opened = true;
      loadDynamicSuggestions();
      streamAssistantMessage(i18n.greeting, '', '').then(renderSuggestions);
    }
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    if (backdrop) {
      backdrop.hidden = true;
      backdrop.setAttribute('aria-hidden', 'true');
    }
    fab.setAttribute('aria-expanded', 'false');
    fab.setAttribute('aria-label', openLabel);
    if (fabLabel) fabLabel.textContent = openLabel;
    document.body.classList.remove('mai-chat-open');
  }

  function sendMessage(text) {
    text = (text || '').trim();
    if (!text || busy) return;
    busy = true;
    hideSuggestions();
    appendBubble('user', formatMessage(text));
    history.push({ role: 'user', content: text });
    input.value = '';
    input.style.height = 'auto';

    showTyping();

    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        message: text,
        history: history.slice(-8),
        lang: lang,
        profile: window.ivtProfile ? window.ivtProfile.toJSON() : null,
        seen_photos: seenPhotos.slice(-50),
      }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          removeTyping();
          throw new Error((res.data && res.data.error) || i18n.error);
        }
        var msg = res.data.message || '';
        var linksHtml = renderLinks(res.data.site_links, res.data.affiliate_links, res.data.map_cards);
        var photosHtml = renderPhotos(res.data.photos);
        (res.data.photos || []).forEach(function (p) {
          if (p && p.url && seenPhotos.indexOf(p.url) === -1) seenPhotos.push(p.url);
        });
        return streamAssistantMessage(msg, linksHtml, photosHtml).then(function () {
          history.push({ role: 'assistant', content: msg });
        });
      })
      .catch(function (err) {
        removeTyping();
        appendBubble('assistant', formatMessage(err.message || i18n.error), 'mai-chat__row--error');
      })
      .finally(function () {
        busy = false;
      });
  }

  fab.addEventListener('click', function () {
    if (isOpen()) closePanel();
    else openPanel();
  });
  if (closeBtn) {
    closeBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      closePanel();
    });
  }
  if (backdrop) {
    backdrop.addEventListener('click', function (e) {
      e.preventDefault();
      closePanel();
    });
  }
  panel.addEventListener('click', function (e) {
    e.stopPropagation();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) closePanel();
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage(input.value);
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  input.addEventListener('input', function () {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 88) + 'px';
  });
})();
