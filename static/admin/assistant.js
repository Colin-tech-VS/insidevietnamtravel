/* Linh 🧭 — copilote IA interne de l'admin (développement & SEO).
   Chat + briefing d'audit à l'ouverture + jobs de génération en arrière-plan
   + cartes de confirmation : aucune publication sans clic « Confirmer ».
   L'état (conversation, panneau ouvert, job en cours, confirmations) est
   conservé en sessionStorage : les liens internes proposés par Linh s'ouvrent
   dans le MÊME onglet et la conversation reste affichée après navigation. */
(function initLinhAssistant() {
  'use strict';

  var root = document.getElementById('linh-chat');
  if (!root) return;

  var fab = document.getElementById('linh-chat-fab');
  var panel = document.getElementById('linh-chat-panel');
  var closeBtn = document.getElementById('linh-chat-close');
  var messagesEl = document.getElementById('linh-chat-messages');
  var suggestionsEl = document.getElementById('linh-chat-suggestions');
  var form = document.getElementById('linh-chat-form');
  var input = document.getElementById('linh-chat-input');

  var apiUrl = root.dataset.apiUrl;
  var searchUrl = root.dataset.searchUrl;
  var insightsUrl = root.dataset.insightsUrl;
  var jobUrlTpl = root.dataset.jobUrl;
  var actionJobUrlTpl = root.dataset.actionJobUrl;
  var confirmUrl = root.dataset.confirmUrl;

  var STORAGE_KEY = 'linhChatState';

  function loadState() {
    try {
      var st = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
      if (st && typeof st === 'object') {
        return {
          open: !!st.open,
          opened: !!st.opened,
          history: Array.isArray(st.history) ? st.history : [],
          items: Array.isArray(st.items) ? st.items : [],
          suggestions: Array.isArray(st.suggestions) ? st.suggestions : [],
          job: typeof st.job === 'string' ? st.job : '',
        };
      }
    } catch (e) { /* sessionStorage indisponible */ }
    return { open: false, opened: false, history: [], items: [], suggestions: [], job: '' };
  }

  var state = loadState();
  var history = state.history;
  var busy = false;
  var jobTimer = 0;

  function saveState() {
    if (history.length > 30) history.splice(0, history.length - 30);
    if (state.items.length > 60) state.items.splice(0, state.items.length - 60);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) { /* quota / navigation privée */ }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatMessage(text, streaming) {
    var html = escapeHtml(String(text || ''));
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="linh-chat__emph">$1</strong>');
    if (streaming) {
      html = html.replace(/\*\*([^*]*)$/, '$1');
    }
    html = html
      .replace(/\n/g, '<br>')
      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    return html;
  }

  /* Lien interne (« /admin/… », « /hanoi »…) : même onglet, la conversation
     est restaurée après navigation. Lien externe : nouvel onglet. */
  function linkAttrs(url) {
    var internal = url.charAt(0) === '/' && url.charAt(1) !== '/';
    return internal ? '' : ' target="_blank" rel="noopener"';
  }

  function scrollBottom() {
    window.requestAnimationFrame(function () {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function appendBubble(role, html, extraClass) {
    var wrap = document.createElement('div');
    wrap.className = 'linh-chat__bubble-wrap linh-chat__bubble-wrap--' + role + (extraClass ? ' ' + extraClass : '');
    var bubble = document.createElement('div');
    bubble.className = 'linh-chat__bubble linh-chat__bubble--' + role;
    bubble.innerHTML = html;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  /* Affiche ET mémorise une bulle (restituée après navigation). */
  function say(role, html, extraClass) {
    var wrap = appendBubble(role, html, extraClass);
    state.items.push({ t: 'b', role: role, html: html, cls: extraClass || '' });
    saveState();
    return wrap;
  }

  function showTyping(label) {
    var html = '<span class="linh-chat__typing">'
      + '<span aria-hidden="true">🧭</span>'
      + '<span class="linh-chat__typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>'
      + '<span class="linh-chat__typing-label">' + escapeHtml(label || 'Linh analyse le site…') + '</span>'
      + '</span>';
    var wrap = appendBubble('assistant', html, 'linh-chat__bubble-wrap--typing');
    wrap.dataset.typing = '1';
    return wrap;
  }

  function removeTyping() {
    var el = messagesEl.querySelector('[data-typing="1"]');
    if (el) el.remove();
  }

  /* ── Effet « machine à écrire » — même rendu que Mai côté public ── */

  var supportsUnicodeProps = (function () {
    try {
      return /\p{Extended_Pictographic}/u.test('🧭');
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

  /* Écrit la réponse progressivement (clic sur la bulle = tout afficher).
     La bulle est mémorisée complète : après navigation, pas de re-animation. */
  function streamSay(text, extraHtml) {
    text = String(text || '');
    extraHtml = extraHtml || '';
    var fullHtml = formatMessage(text) + extraHtml;
    state.items.push({ t: 'b', role: 'assistant', html: fullHtml, cls: '' });
    saveState();

    if (!text) {
      appendBubble('assistant', fullHtml);
      return Promise.resolve();
    }

    return new Promise(function (resolve) {
      var wrap = appendBubble('assistant', '', 'linh-chat__bubble-wrap--streaming');
      wrap.title = 'Cliquer pour afficher tout';
      var bubble = wrap.querySelector('.linh-chat__bubble');
      bubble.classList.add('linh-chat__bubble--streaming');
      bubble.innerHTML = '<span class="linh-chat__stream-text"></span>'
        + '<span class="linh-chat__cursor" aria-hidden="true"></span>';

      var textEl = bubble.querySelector('.linh-chat__stream-text');
      var units = buildStreamUnits(text);
      var unitIndex = 0;
      var acc = '';
      var done = false;
      var rafId = 0;
      var carryMs = 0;
      var lastTs = 0;

      function finishInstant() {
        if (done) return;
        done = true;
        if (rafId) window.cancelAnimationFrame(rafId);
        bubble.classList.remove('linh-chat__bubble--streaming');
        wrap.classList.remove('linh-chat__bubble-wrap--streaming');
        wrap.removeAttribute('title');
        bubble.innerHTML = fullHtml;
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

  function renderActions(actions) {
    if (!actions || !actions.length) return '';
    var html = '<div class="linh-chat__actions">';
    actions.forEach(function (a) {
      html += '<a class="linh-chat__action" href="' + escapeHtml(a.url) + '"' + linkAttrs(a.url) + '>'
        + '<span>' + escapeHtml(a.label) + '</span><span aria-hidden="true">→</span></a>';
    });
    html += '</div>';
    return html;
  }

  function renderFindings(findings) {
    if (!findings || !findings.length) return '';
    var html = '<div class="linh-chat__findings">';
    findings.forEach(function (f) {
      html += '<div class="linh-chat__finding linh-chat__finding--' + escapeHtml(f.severity || 'info') + '">'
        + '<span class="linh-chat__finding-icon" aria-hidden="true">' + escapeHtml(f.icon || '•') + '</span>'
        + '<div class="linh-chat__finding-body">'
        + '<strong>' + escapeHtml(f.title) + '</strong>'
        + '<small>' + escapeHtml(f.detail) + '</small>'
        + (f.url ? '<a href="' + escapeHtml(f.url) + '"' + linkAttrs(f.url) + '>Ouvrir →</a>' : '')
        + '</div>'
        + '<span class="linh-chat__finding-sev">' + escapeHtml(f.severity || '') + '</span>'
        + '</div>';
    });
    html += '</div>';
    return html;
  }

  function postConfirm(token, decision) {
    return fetch(confirmUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ token: token, decision: decision }),
    }).then(function (r) {
      return r.json().then(function (d) { return { ok: r.ok && d.ok, data: d }; });
    });
  }

  function markConfirmDone(token) {
    state.items.forEach(function (item) {
      if (item.t === 'c' && item.confirm && item.confirm.token === token) item.done = true;
    });
    saveState();
  }

  function renderConfirmCard(confirm, opts) {
    if (!confirm || !confirm.token) return;
    opts = opts || {};
    if (!opts.restored) {
      state.items.push({ t: 'c', confirm: confirm, done: false });
      saveState();
    }
    var wrap = appendBubble('assistant', '', 'linh-chat__bubble-wrap--confirm');
    var bubble = wrap.querySelector('.linh-chat__bubble');
    bubble.classList.add('linh-chat__bubble--confirm');
    bubble.innerHTML = '<div class="linh-chat__confirm">'
      + '<p class="linh-chat__confirm-title">🔒 ' + escapeHtml(confirm.title) + '</p>'
      + '<p class="linh-chat__confirm-summary">' + formatMessage(confirm.summary) + '</p>'
      + '<div class="linh-chat__confirm-btns">'
      + '<button type="button" class="linh-chat__btn linh-chat__btn--ok">Confirmer</button>'
      + '<button type="button" class="linh-chat__btn linh-chat__btn--cancel">Annuler</button>'
      + '</div></div>';

    var okBtn = bubble.querySelector('.linh-chat__btn--ok');
    var cancelBtn = bubble.querySelector('.linh-chat__btn--cancel');

    function disable() {
      okBtn.disabled = true;
      cancelBtn.disabled = true;
      bubble.classList.add('linh-chat__bubble--confirm-done');
    }

    if (opts.done) {
      disable();
      return;
    }

    okBtn.addEventListener('click', function () {
      disable();
      markConfirmDone(confirm.token);
      showTyping('Exécution en cours…');
      postConfirm(confirm.token, 'confirm').then(function (res) {
        if (res.ok && res.data.async && res.data.job_token) {
          showTyping(res.data.message || 'Mise à jour en cours…');
          pollActionJob(res.data.job_token);
          saveState();
          return;
        }
        removeTyping();
        if (res.ok) {
          history.push({ role: 'assistant', content: res.data.message || 'Action confirmée et effectuée.' });
          streamSay(res.data.message || '✅ Fait.');
        } else {
          say('assistant', formatMessage('⚠️ ' + (res.data.error || 'Échec de l\'action.')), 'linh-chat__bubble-wrap--error');
        }
        saveState();
        busy = false;
      }).catch(function () {
        removeTyping();
        say('assistant', formatMessage('⚠️ Erreur réseau pendant l\'exécution.'), 'linh-chat__bubble-wrap--error');
        busy = false;
      });
    });

    cancelBtn.addEventListener('click', function () {
      disable();
      markConfirmDone(confirm.token);
      postConfirm(confirm.token, 'cancel').finally(function () {
        history.push({ role: 'assistant', content: 'Action annulée par l\'admin — rien n\'a été fait.' });
        saveState();
        streamSay('Très bien, **rien n\'a été publié**. Le brouillon reste disponible dans l\'admin.');
      });
    });
  }

  function pollJob(kind) {
    if (jobTimer) window.clearTimeout(jobTimer);
    var url = jobUrlTpl.replace('KIND', kind);
    state.job = kind;
    saveState();

    function finish() {
      state.job = '';
      saveState();
      busy = false;
    }

    function tick() {
      fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (st) {
          var typing = messagesEl.querySelector('[data-typing="1"] .linh-chat__typing-label');
          if (st.status === 'running') {
            if (typing && st.phase) typing.textContent = st.phase;
            jobTimer = window.setTimeout(tick, 2500);
            return;
          }
          removeTyping();
          if (st.status === 'done') {
            var extra = st.preview_url
              ? renderActions([{ label: 'Voir l\'aperçu dans l\'admin', url: st.preview_url }])
              : '';
            history.push({ role: 'assistant', content: st.summary || 'Brouillon prêt.' });
            streamSay(st.summary || 'Brouillon prêt.', extra).then(function () {
              if (st.confirm) renderConfirmCard(st.confirm);
            });
          } else if (st.status === 'error') {
            say('assistant', formatMessage('⚠️ ' + (st.error || 'Échec de la génération.')), 'linh-chat__bubble-wrap--error');
          } else {
            say('assistant', formatMessage('⚠️ Génération introuvable (session expirée ?) — relancez la demande.'), 'linh-chat__bubble-wrap--error');
          }
          finish();
        })
        .catch(function () {
          jobTimer = window.setTimeout(tick, 4000);
        });
    }

    jobTimer = window.setTimeout(tick, 2500);
  }

  /* Job d'action lourde (ex. update_image) — hors requête HTTP pour éviter timeout Scalingo. */
  function pollActionJob(jobToken) {
    if (!actionJobUrlTpl || !jobToken) {
      busy = false;
      return;
    }
    if (jobTimer) window.clearTimeout(jobTimer);
    var url = actionJobUrlTpl.replace('TOKEN', encodeURIComponent(jobToken));

    function finish() {
      busy = false;
    }

    function tick() {
      fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (st) {
          var typing = messagesEl.querySelector('[data-typing="1"] .linh-chat__typing-label');
          if (st.status === 'running') {
            if (typing && st.phase) typing.textContent = st.phase;
            jobTimer = window.setTimeout(tick, 2000);
            return;
          }
          removeTyping();
          if (st.status === 'done') {
            var extra = renderActions(st.url ? [{ label: 'Voir la page', url: st.url }] : []);
            history.push({ role: 'assistant', content: st.message || '✅ Fait.' });
            streamSay(st.message || '✅ Fait.', extra);
          } else if (st.status === 'error') {
            say('assistant', formatMessage('⚠️ ' + (st.error || 'Échec de l\'action.')), 'linh-chat__bubble-wrap--error');
          } else {
            say('assistant', formatMessage('⚠️ Action introuvable (session expirée ?) — relancez la demande.'), 'linh-chat__bubble-wrap--error');
          }
          saveState();
          finish();
        })
        .catch(function () {
          jobTimer = window.setTimeout(tick, 3000);
        });
    }

    jobTimer = window.setTimeout(tick, 1500);
  }

  function renderSuggestions() {
    if (!suggestionsEl || !state.suggestions.length) return;
    suggestionsEl.innerHTML = '';
    state.suggestions.forEach(function (q) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'linh-chat__chip';
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
    state.suggestions = [];
    saveState();
  }

  function loadInsights() {
    showTyping('Linh audite le site…');
    fetch(insightsUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        removeTyping();
        if (!data.ok) {
          say('assistant', formatMessage('⚠️ ' + (data.error || 'Briefing indisponible.')), 'linh-chat__bubble-wrap--error');
          return;
        }
        state.suggestions = data.suggestions || [];
        history.push({ role: 'assistant', content: data.greeting || '' });
        saveState();
        streamSay(data.greeting || '', renderFindings(data.findings)).then(renderSuggestions);
      })
      .catch(function () {
        removeTyping();
        appendBubble('assistant', formatMessage('⚠️ Impossible de charger le briefing.'), 'linh-chat__bubble-wrap--error');
      });
  }

  /* Affiche une réponse de Linh (message, aperçus, actions, confirmation),
     puis enchaîne : recherche web (loader + 2e appel automatique), job de
     génération, ou rend la main. */
  function handleReply(d, originalText) {
    var extra = '';
    if (d.post_preview) {
      extra += '<div class="linh-chat__post-preview">' + formatMessage(d.post_preview) + '</div>';
    }
    extra += renderFindings(d.findings);
    extra += renderActions(d.actions);
    history.push({ role: 'assistant', content: d.message || '' });
    saveState();

    var streamed = (d.message || extra)
      ? streamSay(d.message || '', extra)
      : Promise.resolve();

    streamed.then(function () {
      if (d.confirm) renderConfirmCard(d.confirm);

      if (d.search && d.search.query) {
        runWebSearch(d.search.query, originalText); // busy reste true pendant la recherche
      } else if (d.job && d.job.kind) {
        showTyping('Génération en cours…');
        pollJob(d.job.kind); // busy reste true jusqu'à la fin du job
      } else if (d.action_job && d.action_job.token) {
        showTyping(d.message || 'Action en cours…');
        pollActionJob(d.action_job.token);
      } else {
        busy = false;
      }
    });
  }

  /* Recherche web en deux temps : Linh a annoncé sa recherche, on affiche un
     loader dédié, le serveur interroge DuckDuckGo puis Linh revient toute
     seule avec sa réponse sourcée (résultats réels). */
  function runWebSearch(query, originalText) {
    showTyping('🔍 Recherche sur internet…');
    fetch(searchUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ query: query, message: originalText || '', history: history.slice(-10) }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        removeTyping();
        if (!res.ok || !res.data.ok) {
          throw new Error((res.data && res.data.error) || 'Recherche web indisponible.');
        }
        handleReply(res.data, originalText);
      })
      .catch(function (err) {
        removeTyping();
        say('assistant', formatMessage('⚠️ ' + (err.message || 'Recherche web indisponible.')), 'linh-chat__bubble-wrap--error');
        busy = false;
      });
  }

  function sendMessage(text) {
    text = (text || '').trim();
    if (!text || busy) return;
    busy = true;
    hideSuggestions();
    say('user', formatMessage(text));
    history.push({ role: 'user', content: text });
    saveState();
    input.value = '';
    input.style.height = 'auto';
    showTyping('Linh analyse le site…');

    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ message: text, history: history.slice(-10) }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          removeTyping();
          throw new Error((res.data && res.data.error) || 'Erreur.');
        }
        removeTyping();
        handleReply(res.data, text);
      })
      .catch(function (err) {
        removeTyping();
        appendBubble('assistant', formatMessage(err.message || 'Erreur.'), 'linh-chat__bubble-wrap--error');
        busy = false;
      });
  }

  function isOpen() {
    return !panel.hidden;
  }

  function openPanel() {
    panel.hidden = false;
    fab.setAttribute('aria-expanded', 'true');
    state.open = true;
    if (!state.opened) {
      state.opened = true;
      saveState();
      loadInsights();
    } else {
      saveState();
    }
    input.focus();
    scrollBottom();
  }

  function closePanel() {
    panel.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
    state.open = false;
    saveState();
  }

  fab.addEventListener('click', function () {
    if (isOpen()) closePanel();
    else openPanel();
  });
  if (closeBtn) closeBtn.addEventListener('click', closePanel);
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
    input.style.height = Math.min(input.scrollHeight, 96) + 'px';
  });

  /* ── Restauration après navigation ── */
  state.items.forEach(function (item) {
    if (item.t === 'b') appendBubble(item.role, item.html, item.cls);
    else if (item.t === 'c') renderConfirmCard(item.confirm, { restored: true, done: item.done });
  });
  renderSuggestions();
  if (state.job) {
    busy = true;
    showTyping('Génération en cours…');
    pollJob(state.job);
  }
  if (state.open) openPanel();
})();
