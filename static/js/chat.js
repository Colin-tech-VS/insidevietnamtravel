(function initMaiChat() {
  'use strict';

  var root = document.getElementById('mai-chat');
  if (!root) return;

  var fab = document.getElementById('mai-chat-fab');
  var fabLabel = document.getElementById('mai-chat-fab-label');
  var panel = document.getElementById('mai-chat-panel');
  var backdrop = document.getElementById('mai-chat-backdrop');
  var closeBtn = document.getElementById('mai-chat-close');
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
  };

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

  function formatMessage(text) {
    return escapeHtml(text)
      .replace(/\n/g, '<br>')
      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
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

  function renderLinks(siteLinks, affiliateLinks) {
    if ((!siteLinks || !siteLinks.length) && (!affiliateLinks || !affiliateLinks.length)) return '';
    var html = '<div class="mai-chat__links">';
    (siteLinks || []).forEach(function (l) {
      html += '<a class="mai-chat__link mai-chat__link--site" href="' + escapeHtml(l.url) + '" target="_blank" rel="noopener">'
        + '🔗 ' + escapeHtml(l.title) + '</a>';
    });
    (affiliateLinks || []).forEach(function (l) {
      html += '<a class="mai-chat__link mai-chat__link--aff" href="' + escapeHtml(l.url) + '" target="_blank" rel="noopener sponsored">'
        + '<span class="mai-chat__link-badge">' + escapeHtml(i18n.affiliate) + '</span> '
        + escapeHtml(l.label)
        + (l.teaser ? '<small>' + escapeHtml(l.teaser) + '</small>' : '')
        + '</a>';
    });
    html += '</div>';
    return html;
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

  function tokenizeStream(text) {
    return String(text || '').match(/[^\s]+|\s+/g) || [];
  }

  function streamDelay(token, index, total) {
    var delay = 22;
    if (/^\s+$/.test(token)) return 6;
    if (/[.!?…]$/.test(token.trim())) return delay + 140;
    if (/[,;:]$/.test(token.trim())) return delay + 70;
    if (/\p{Extended_Pictographic}/u.test(token)) return delay + 35;
    var ratio = index / Math.max(total, 1);
    if (ratio > 0.55) delay *= 0.72;
    if (ratio > 0.8) delay *= 0.58;
    return delay + (index % 3) * 4;
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
      var tokens = tokenizeStream(text);
      var idx = 0;
      var acc = '';
      var done = false;
      var timer = null;

      function revealLinks() {
        if (!linksHtml) return;
        var holder = document.createElement('div');
        holder.innerHTML = linksHtml.trim();
        var linksEl = holder.firstElementChild;
        if (!linksEl) return;
        linksEl.classList.add('mai-chat__links--reveal');
        bubble.appendChild(linksEl);
        scrollBottom();
      }

      function finishInstant() {
        if (done) return;
        done = true;
        if (timer) clearTimeout(timer);
        textEl.innerHTML = formatMessage(text);
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

      function step() {
        if (done) return;
        if (idx >= tokens.length) {
          finishInstant();
          return;
        }
        acc += tokens[idx];
        idx += 1;
        textEl.innerHTML = formatMessage(acc);
        scrollBottom();
        timer = window.setTimeout(step, streamDelay(tokens[idx - 1], idx, tokens.length));
      }

      wrap.addEventListener('click', onSkip);
      step();
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
      body: JSON.stringify({ message: text, history: history.slice(-8), lang: lang }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          removeTyping();
          throw new Error((res.data && res.data.error) || i18n.error);
        }
        var msg = res.data.message || '';
        var linksHtml = renderLinks(res.data.site_links, res.data.affiliate_links);
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
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
})();
