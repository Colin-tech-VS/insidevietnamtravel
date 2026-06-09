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
  var busy = false;
  var opened = false;

  var i18n = {
    typing: root.dataset.typing || '…',
    error: root.dataset.error || 'Error',
    affiliate: root.dataset.affiliateBadge || 'Partner',
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
  var SIZE_DEFAULT_W = 320;
  var SIZE_DEFAULT_H = 480;
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

  function formatMessage(text, streaming) {
    var escaped = escapeHtml(String(text || ''));
    escaped = applyEmphasis(escaped, !!streaming);
    escaped = escaped
      .replace(/\n/g, '<br>')
      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    return escaped;
  }

  var scrollRaf = 0;
  function scrollBottom() {
    if (scrollRaf) return;
    scrollRaf = window.requestAnimationFrame(function () {
      scrollRaf = 0;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function appendBubble(role, html, extraClass) {
    var wrap = document.createElement('div');
    wrap.className = 'mai-chat__bubble-wrap mai-chat__bubble-wrap--' + role + (extraClass ? ' ' + extraClass : '');
    var bubble = document.createElement('div');
    bubble.className = 'mai-chat__bubble mai-chat__bubble--' + role;
    bubble.innerHTML = html;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function renderMapCard(card) {
    var mapId = (window.maiChatMaps && window.maiChatMaps.nextId)
      ? window.maiChatMaps.nextId()
      : ('mai-map-' + Math.random().toString(36).slice(2, 8));
    var pointsJson = escapeHtml(JSON.stringify(card.points || []));
    var html = '<article class="mai-chat__map-card">';
    html += '<header class="mai-chat__map-head">';
    html += '<span class="mai-chat__map-icon" aria-hidden="true">🗺️</span>';
    html += '<div class="mai-chat__map-head-text">';
    html += '<strong class="mai-chat__map-title">' + escapeHtml(card.name || card.slug) + '</strong>';
    html += '<span class="mai-chat__map-sub">' + escapeHtml(i18n.mapSubtitle) + '</span>';
    html += '</div></header>';
    html += '<div class="mai-chat__map-canvas" id="' + mapId + '" data-points="' + pointsJson + '" data-error="' + escapeHtml(i18n.mapError) + '" role="img" aria-label="' + escapeHtml(card.name || '') + '"></div>';

    if (card.points && card.points.length) {
      html += '<p class="mai-chat__map-pins-label">' + escapeHtml(i18n.mapOn) + '</p>';
      html += '<ul class="mai-chat__map-pins">';
      card.points.forEach(function (p) {
        var kindClass = 'mai-chat__pin-kind--' + escapeHtml(p.kind || 'poi');
        html += '<li class="mai-chat__map-pin' + (p.highlight ? ' mai-chat__map-pin--highlight' : '') + '">';
        html += '<span class="mai-chat__pin-kind ' + kindClass + '" aria-hidden="true"></span>';
        html += '<div class="mai-chat__pin-body">';
        html += '<strong>' + escapeHtml(p.title) + '</strong>';
        if (p.kind_label) html += '<span class="mai-chat__pin-meta">' + escapeHtml(p.kind_label) + '</span>';
        if (p.price_hint) html += '<span class="mai-chat__pin-price">' + escapeHtml(p.price_hint) + '</span>';
        if (p.affiliate_url) {
          html += '<a class="mai-chat__pin-cta" href="' + escapeHtml(p.affiliate_url) + '" target="_blank" rel="noopener sponsored">'
            + escapeHtml(p.affiliate_cta || (lang === 'en' ? 'Book' : 'Réserver')) + ' ↗</a>';
        }
        html += '</div></li>';
      });
      html += '</ul>';
    }

    if (card.map_url) {
      html += '<a class="mai-chat__map-cta" href="' + escapeHtml(card.map_url) + '" target="_blank" rel="noopener">'
        + escapeHtml(i18n.mapCta) + ' →</a>';
    }
    html += '</article>';
    return html;
  }

  function renderLinks(siteLinks, affiliateLinks, mapCards) {
    if ((!siteLinks || !siteLinks.length) && (!affiliateLinks || !affiliateLinks.length)
        && (!mapCards || !mapCards.length)) return '';
    var html = '<div class="mai-chat__links">';

    (mapCards || []).forEach(function (card) {
      html += renderMapCard(card);
    });

    (siteLinks || []).forEach(function (l) {
      html += '<a class="mai-chat__link-card mai-chat__link-card--site" href="' + escapeHtml(l.url) + '" target="_blank" rel="noopener">'
        + '<span class="mai-chat__link-card-icon" aria-hidden="true">📖</span>'
        + '<span class="mai-chat__link-card-body"><strong>' + escapeHtml(l.title) + '</strong></span>'
        + '<span class="mai-chat__link-card-arrow" aria-hidden="true">→</span></a>';
    });

    (affiliateLinks || []).forEach(function (l) {
      html += '<a class="mai-chat__link-card mai-chat__link-card--aff" href="' + escapeHtml(l.url) + '" target="_blank" rel="noopener sponsored">'
        + '<span class="mai-chat__link-card-icon" aria-hidden="true">✦</span>'
        + '<span class="mai-chat__link-card-body">'
        + '<span class="mai-chat__link-badge">' + escapeHtml(i18n.affiliate) + '</span> '
        + '<strong>' + escapeHtml(l.label) + '</strong>'
        + (l.teaser ? '<small>' + escapeHtml(l.teaser) + '</small>' : '')
        + '</span>'
        + '<span class="mai-chat__link-card-arrow" aria-hidden="true">↗</span></a>';
    });

    html += '</div>';
    return html;
  }

  function initMapsInLinks(linksEl) {
    if (window.maiChatMaps && linksEl) {
      window.maiChatMaps.initIn(linksEl);
    }
  }

  function showTyping() {
    var html = '<span class="mai-chat__typing">'
      + '<span class="mai-chat__typing-avatar" aria-hidden="true">🌸</span>'
      + '<span class="mai-chat__typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>'
      + '<span class="mai-chat__typing-label">' + escapeHtml(i18n.typing) + '</span>'
      + '</span>';
    var wrap = appendBubble('assistant', html, 'mai-chat__bubble-wrap--typing');
    wrap.dataset.typing = '1';
    return wrap;
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
    var chars = Array.from(String(text || ''));
    var units = [];
    var i = 0;
    while (i < chars.length) {
      var ch = chars[i];
      if (/\s/.test(ch)) {
        units.push(ch);
        i += 1;
        continue;
      }
      if (isEmojiChar(ch) || /[.!?,;:…]/.test(ch)) {
        units.push(ch);
        i += 1;
        continue;
      }
      var size = 1;
      if (i + 1 < chars.length && !/\s/.test(chars[i + 1]) && !isEmojiChar(chars[i + 1])) {
        size = 2;
      }
      units.push(chars.slice(i, i + size).join(''));
      i += size;
    }
    return units;
  }

  function unitPause(unit, progress) {
    if (/^\s+$/.test(unit)) return 10;
    if (/[.!?…]/.test(unit)) return 52;
    if (/[,;:]/.test(unit)) return 32;
    if (isEmojiChar(unit)) return 28;
    var ms = 16;
    if (progress > 0.45) ms *= 0.78;
    if (progress > 0.72) ms *= 0.68;
    return ms;
  }

  function streamAssistantMessage(text, linksHtml) {
    return new Promise(function (resolve) {
      removeTyping();

      var wrap = document.createElement('div');
      wrap.className = 'mai-chat__bubble-wrap mai-chat__bubble-wrap--assistant mai-chat__bubble-wrap--streaming';
      wrap.title = lang === 'en' ? 'Click to show full message' : 'Cliquer pour afficher tout';

      var bubble = document.createElement('div');
      bubble.className = 'mai-chat__bubble mai-chat__bubble--assistant mai-chat__bubble--streaming';
      bubble.innerHTML = '<div class="mai-chat__stream">'
        + '<span class="mai-chat__stream-text"></span>'
        + '<span class="mai-chat__cursor" aria-hidden="true"></span>'
        + '</div>';

      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
      scrollBottom();

      var textEl = bubble.querySelector('.mai-chat__stream-text');
      var units = buildStreamUnits(text);
      var unitIndex = 0;
      var acc = '';
      var done = false;
      var rafId = 0;
      var carryMs = 0;
      var lastTs = 0;

      function revealLinks() {
        if (!linksHtml) return;
        var holder = document.createElement('div');
        holder.innerHTML = linksHtml.trim();
        var linksEl = holder.firstElementChild;
        if (!linksEl) return;
        linksEl.classList.add('mai-chat__links--reveal');
        bubble.appendChild(linksEl);
        initMapsInLinks(linksEl);
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
        wrap.classList.remove('mai-chat__bubble-wrap--streaming');
        wrap.removeAttribute('title');
        revealLinks();
        scrollBottom();
        wrap.removeEventListener('click', onSkip);
        resolve();
      }

      function onSkip(e) {
        if (e.target.closest('a')) return;
        finishInstant();
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

      wrap.addEventListener('click', onSkip);
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
      streamAssistantMessage(i18n.greeting, '').then(renderSuggestions);
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
        return streamAssistantMessage(msg, linksHtml).then(function () {
          history.push({ role: 'assistant', content: msg });
        });
      })
      .catch(function (err) {
        removeTyping();
        appendBubble('assistant', formatMessage(err.message || i18n.error), 'mai-chat__bubble-wrap--error');
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
