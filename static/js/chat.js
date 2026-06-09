(function initMaiChat() {
  'use strict';

  var root = document.getElementById('mai-chat');
  if (!root) return;

  var fab = document.getElementById('mai-chat-fab');
  var panel = document.getElementById('mai-chat-panel');
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
    var wrap = appendBubble('assistant', '<span class="mai-chat__typing"><span></span><span></span><span></span> ' + escapeHtml(i18n.typing) + '</span>', 'mai-chat__bubble-wrap--typing');
    wrap.dataset.typing = '1';
    return wrap;
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

  function openPanel() {
    panel.hidden = false;
    fab.setAttribute('aria-expanded', 'true');
    document.body.classList.add('mai-chat-open');
    if (!opened) {
      opened = true;
      appendBubble('assistant', formatMessage(i18n.greeting));
      renderSuggestions();
    }
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
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

    var typing = showTyping();

    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ message: text, history: history.slice(-8), lang: lang }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        removeTyping();
        if (!res.ok || !res.data.ok) {
          throw new Error((res.data && res.data.error) || i18n.error);
        }
        var msg = res.data.message || '';
        var linksHtml = renderLinks(res.data.site_links, res.data.affiliate_links);
        appendBubble('assistant', formatMessage(msg) + linksHtml);
        history.push({ role: 'assistant', content: msg });
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
    if (panel.hidden) openPanel();
    else closePanel();
  });
  closeBtn.addEventListener('click', closePanel);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) closePanel();
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
