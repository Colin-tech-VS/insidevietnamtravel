/* Linh 🧭 — copilote IA interne de l'admin (développement & SEO).
   Chat + briefing d'audit à l'ouverture + jobs de génération en arrière-plan
   + cartes de confirmation : aucune publication sans clic « Confirmer ». */
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
  var insightsUrl = root.dataset.insightsUrl;
  var jobUrlTpl = root.dataset.jobUrl;
  var confirmUrl = root.dataset.confirmUrl;

  var history = [];
  var suggestions = [];
  var busy = false;
  var opened = false;
  var jobTimer = 0;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatMessage(text) {
    var html = escapeHtml(String(text || ''));
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="linh-chat__emph">$1</strong>');
    html = html
      .replace(/\n/g, '<br>')
      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    return html;
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

  function renderActions(actions) {
    if (!actions || !actions.length) return '';
    var html = '<div class="linh-chat__actions">';
    actions.forEach(function (a) {
      html += '<a class="linh-chat__action" href="' + escapeHtml(a.url) + '" target="_blank" rel="noopener">'
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
        + (f.url ? '<a href="' + escapeHtml(f.url) + '" target="_blank" rel="noopener">Ouvrir →</a>' : '')
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

  function renderConfirmCard(confirm) {
    if (!confirm || !confirm.token) return;
    var wrap = appendBubble('assistant', '', 'linh-chat__bubble-wrap--confirm');
    var bubble = wrap.querySelector('.linh-chat__bubble');
    bubble.classList.add('linh-chat__bubble--confirm');
    bubble.innerHTML = '<div class="linh-chat__confirm">'
      + '<p class="linh-chat__confirm-title">🔒 ' + escapeHtml(confirm.title) + '</p>'
      + '<p class="linh-chat__confirm-summary">' + formatMessage(confirm.summary) + '</p>'
      + '<div class="linh-chat__confirm-btns">'
      + '<button type="button" class="linh-chat__btn linh-chat__btn--ok">Confirmer la publication</button>'
      + '<button type="button" class="linh-chat__btn linh-chat__btn--cancel">Annuler</button>'
      + '</div></div>';

    var okBtn = bubble.querySelector('.linh-chat__btn--ok');
    var cancelBtn = bubble.querySelector('.linh-chat__btn--cancel');

    function disable() {
      okBtn.disabled = true;
      cancelBtn.disabled = true;
      bubble.classList.add('linh-chat__bubble--confirm-done');
    }

    okBtn.addEventListener('click', function () {
      disable();
      showTyping('Publication en cours…');
      postConfirm(confirm.token, 'confirm').then(function (res) {
        removeTyping();
        if (res.ok) {
          appendBubble('assistant', formatMessage(res.data.message || '✅ Fait.'));
          history.push({ role: 'assistant', content: res.data.message || 'Publication confirmée et effectuée.' });
        } else {
          appendBubble('assistant', formatMessage('⚠️ ' + (res.data.error || 'Échec de la publication.')), 'linh-chat__bubble-wrap--error');
        }
      }).catch(function () {
        removeTyping();
        appendBubble('assistant', formatMessage('⚠️ Erreur réseau pendant la publication.'), 'linh-chat__bubble-wrap--error');
      });
    });

    cancelBtn.addEventListener('click', function () {
      disable();
      postConfirm(confirm.token, 'cancel').finally(function () {
        appendBubble('assistant', formatMessage('Très bien, **rien n\'a été publié**. Le brouillon reste disponible dans l\'admin.'));
        history.push({ role: 'assistant', content: 'Publication annulée par l\'admin — rien n\'a été publié.' });
      });
    });
  }

  function pollJob(kind) {
    if (jobTimer) window.clearTimeout(jobTimer);
    var url = jobUrlTpl.replace('KIND', kind);

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
            var html = formatMessage(st.summary || 'Brouillon prêt.');
            if (st.preview_url) {
              html += renderActions([{ label: 'Voir l\'aperçu dans l\'admin', url: st.preview_url }]);
            }
            appendBubble('assistant', html);
            history.push({ role: 'assistant', content: st.summary || 'Brouillon prêt.' });
            if (st.confirm) renderConfirmCard(st.confirm);
          } else if (st.status === 'error') {
            appendBubble('assistant', formatMessage('⚠️ ' + (st.error || 'Échec de la génération.')), 'linh-chat__bubble-wrap--error');
          }
          busy = false;
        })
        .catch(function () {
          jobTimer = window.setTimeout(tick, 4000);
        });
    }

    jobTimer = window.setTimeout(tick, 2500);
  }

  function renderSuggestions() {
    if (!suggestionsEl || !suggestions.length) return;
    suggestionsEl.innerHTML = '';
    suggestions.forEach(function (q) {
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
  }

  function loadInsights() {
    showTyping('Linh audite le site…');
    fetch(insightsUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        removeTyping();
        if (!data.ok) {
          appendBubble('assistant', formatMessage('⚠️ ' + (data.error || 'Briefing indisponible.')), 'linh-chat__bubble-wrap--error');
          return;
        }
        suggestions = data.suggestions || [];
        var html = formatMessage(data.greeting || '');
        html += renderFindings(data.findings);
        appendBubble('assistant', html);
        history.push({ role: 'assistant', content: data.greeting || '' });
        renderSuggestions();
      })
      .catch(function () {
        removeTyping();
        appendBubble('assistant', formatMessage('⚠️ Impossible de charger le briefing.'), 'linh-chat__bubble-wrap--error');
      });
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
        var d = res.data;
        removeTyping();
        var html = formatMessage(d.message || '');
        if (d.post_preview) {
          html += '<div class="linh-chat__post-preview">' + formatMessage(d.post_preview) + '</div>';
        }
        html += renderFindings(d.findings);
        html += renderActions(d.actions);
        if (d.message || d.findings || d.actions || d.post_preview) {
          appendBubble('assistant', html);
        }
        history.push({ role: 'assistant', content: d.message || '' });

        if (d.confirm) renderConfirmCard(d.confirm);

        if (d.job && d.job.kind) {
          showTyping('Génération en cours…');
          pollJob(d.job.kind); // busy reste true jusqu'à la fin du job
        } else {
          busy = false;
        }
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
    if (!opened) {
      opened = true;
      loadInsights();
    }
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
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
})();
