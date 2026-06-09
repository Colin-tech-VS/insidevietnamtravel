document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('guide-form-ai');
  const topicInput = document.getElementById('topic');
  const citySelect = document.getElementById('city');
  const overlay = document.getElementById('ai-loader');
  const loaderText = document.getElementById('ai-loader-text');
  const loaderBar = document.getElementById('ai-loader-bar');
  const loaderElapsed = document.getElementById('ai-loader-elapsed');

  let elapsedTimer = null;
  let loaderStart = 0;
  let barPct = 0;       // largeur affichée de la barre
  let barFloor = 0;     // palier de la phase en cours (la barre ne redescend jamais)

  function fmtElapsed(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  // Palier de progression calé sur l'étape RÉELLE renvoyée par le serveur : chaque
  // valeur correspond à une phase concrète du job (rédaction → enrichissement →
  // traduction → image). Entre deux phases, la barre avance doucement toute seule
  // (cf. tick du chrono) pour ne jamais paraître figée pendant une rédaction longue.
  function progressForPhase(phase) {
    const p = (phase || '').toLowerCase();
    if (p.includes('connexion')) return 8;
    if (p.includes('amélioration') || p.includes('analyse')) return 25;
    if (p.includes('rédaction')) return 25;
    if (p.includes('enrichissement')) return 48;
    if (p.includes('traduction')) return 68;
    if (p.includes('image')) return 85;
    if (p.includes('finalisation')) return 95;
    return null;
  }

  function renderBar() {
    if (loaderBar) loaderBar.style.width = `${barPct}%`;
  }

  function setBarFloor(pct) {
    if (pct == null) return;
    barFloor = pct;
    if (barPct < pct) {
      barPct = pct;
      renderBar();
    }
  }

  // Avance lentement vers (palier + 12), plafonné à 94 % tant que ce n'est pas fini :
  // mouvement continu rassurant sans « mentir » en atteignant 100 % avant l'heure.
  function creepBar() {
    const ceiling = Math.min(94, barFloor + 12);
    if (barPct < ceiling) {
      barPct = Math.min(ceiling, barPct + 0.6);
      renderBar();
    }
  }

  document.querySelectorAll('.content-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      document.querySelectorAll('.content-tab').forEach((t) => {
        const active = t.dataset.tab === target;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      document.querySelectorAll('.content-panel').forEach((panel) => {
        panel.hidden = panel.id !== `tab-${target}`;
      });
    });
  });

  // Le texte du modal reflète l'étape RÉELLE renvoyée par le serveur (phase du job)
  // plutôt qu'une liste de phrases qui défilent au hasard sur un minuteur.
  function startLoader(initialText) {
    if (!overlay) return;
    overlay.hidden = false;
    overlay.setAttribute('aria-busy', 'true');
    if (loaderText) loaderText.textContent = initialText || 'Préparation…';
    barPct = 5;
    barFloor = 5;
    renderBar();
    loaderStart = Date.now();
    if (loaderElapsed) loaderElapsed.textContent = '0:00';
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = setInterval(() => {
      if (loaderElapsed) loaderElapsed.textContent = fmtElapsed(Date.now() - loaderStart);
      creepBar();
    }, 1000);
  }

  function setPhase(phase) {
    if (phase && loaderText) loaderText.textContent = phase;
    setBarFloor(progressForPhase(phase));
  }

  function stopLoader() {
    if (elapsedTimer) {
      clearInterval(elapsedTimer);
      elapsedTimer = null;
    }
    barPct = 100;
    barFloor = 100;
    renderBar();
    if (overlay) {
      overlay.hidden = true;
      overlay.removeAttribute('aria-busy');
    }
  }

  async function postJson(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      throw new Error(data.error || 'Erreur lors de la génération');
    }
    return data;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // La génération tourne côté serveur en tâche de fond : on interroge le statut
  // jusqu'à done/error. Plus de "Failed to fetch" même si Groq impose des pauses.
  //
  // On NE coupe PAS tant que le serveur signale une progression. Sur le palier
  // gratuit, une génération (plusieurs appels IA enchaînés + pauses anti rate-limit)
  // peut légitimement durer plusieurs minutes : la tâche de fond continue et finira
  // par déposer le brouillon. On n'abandonne donc qu'en cas de perte de contact
  // prolongée (idleMs) ou au-delà d'un plafond absolu de sécurité (thread figé /
  // process redémarré). Un simple plafond de temps total coupait des générations
  // pourtant encore en cours — c'était la cause du « ça coupe ».
  async function pollDraft(statusUrl, { idleMs = 180000, hardCapMs = 1200000 } = {}) {
    const start = Date.now();
    let lastAlive = Date.now();
    while (Date.now() - start < hardCapMs) {
      await sleep(2500);
      let st;
      try {
        const res = await fetch(statusUrl, {
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' },
        });
        st = await res.json();
      } catch (e) {
        // micro-coupure réseau : on retente sans réinitialiser le minuteur d'inactivité
        if (Date.now() - lastAlive > idleMs) {
          throw new Error('Connexion au serveur perdue. Rafraîchissez la page dans un instant.');
        }
        continue;
      }
      if (st.status === 'done') return;
      if (st.status === 'error') throw new Error(st.error || 'Échec de la génération.');
      if (st.status === 'missing') throw new Error('Session expirée — relancez la génération.');
      lastAlive = Date.now(); // job vivant (running) → on repousse l'échéance d'inactivité
      setPhase(st.phase); // affiche l'étape réelle en cours
    }
    throw new Error('Génération anormalement longue. Rafraîchissez la page dans un instant.');
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const city = citySelect?.value;
      const topic = topicInput?.value?.trim();
      const guideType = form.querySelector('input[name="guide_type"]:checked')?.value;

      if (!city || !topic) {
        form.reportValidity();
        return;
      }

      const btn = form.querySelector('.btn-generate');
      if (btn) btn.disabled = true;
      startLoader('Connexion au moteur IA…');

      try {
        await postJson('/admin/api/guides/generate', {
          city,
          topic,
          guide_type: guideType,
        });
        await pollDraft('/admin/api/guides/draft-status');
        await softReload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  }

  // Recharge l'aperçu dynamiquement (sans navigation, comme les onglets) :
  // on récupère la page, on remplace #draft-slot et on rebranche l'amélioration.
  async function softReload() {
    try {
      const res = await fetch(window.location.href, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'fetch' },
      });
      const html = await res.text();
      const fresh = new DOMParser().parseFromString(html, 'text/html').getElementById('draft-slot');
      const slot = document.getElementById('draft-slot');
      if (fresh && slot) {
        slot.innerHTML = fresh.innerHTML;
        bindImproveForms();
        stopLoader();
        slot.querySelector('.draft-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }
    } catch (e) { /* repli ci-dessous */ }
    window.location.reload();
  }

  function bindImproveForms() {
    document.querySelectorAll('.draft-action-form--improve').forEach((improveForm) => {
      if (improveForm.dataset.bound) return;
      improveForm.dataset.bound = '1';
      improveForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const instructions = improveForm.querySelector('[name="instructions"]')?.value
          || 'Améliore le SEO pour voyageurs préparant un voyage au Vietnam.';
        const btn = improveForm.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        startLoader('Connexion au moteur IA…');

        try {
          await postJson('/admin/api/guides/improve', { instructions });
          await pollDraft('/admin/api/guides/draft-status');
          await softReload();
        } catch (err) {
          stopLoader();
          alert(err.message);
          if (btn) btn.disabled = false;
        }
      });
    });
  }

  bindImproveForms();

  function bindSuggestionCards() {
    document.querySelectorAll('.suggestion-card').forEach((btn) => {
    btn.addEventListener('click', () => {
      const topic = btn.dataset.topic;
      const city = btn.dataset.city;
      const type = btn.dataset.type;

      if (topicInput) topicInput.value = topic;

      if (citySelect && city) {
        const option = [...citySelect.options].find((o) => o.value === city);
        if (option) citySelect.value = city;
      }

      const typeRadio = document.querySelector(`input[name="guide_type"][value="${type}"]`);
      if (typeRadio) typeRadio.checked = true;

      btn.classList.add('is-selected');
      setTimeout(() => btn.classList.remove('is-selected'), 600);

      topicInput?.focus();
      form?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    });
  }

  bindSuggestionCards();

  const refreshBtn = document.getElementById('refresh-suggestions');
  const suggestionsList = document.getElementById('suggestions-list');
  if (refreshBtn && suggestionsList) {
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.disabled = true;
      const prev = refreshBtn.textContent;
      refreshBtn.textContent = '…';
      try {
        const data = await postJson('/admin/api/guides/suggestions', {});
        suggestionsList.innerHTML = (data.suggestions || []).map((s) => `
          <li>
            <button type="button" class="suggestion-card" data-topic="${escapeHtml(s.topic)}" data-city="${escapeHtml(s.city)}" data-type="${escapeHtml(s.guide_type)}">
              <span class="suggestion-card__priority suggestion-card__priority--${escapeHtml(s.priority || 'moyenne')}">${escapeHtml(s.priority || 'moyenne')}</span>
              <span class="suggestion-card__topic">${escapeHtml(s.topic)}</span>
              <span class="suggestion-card__meta">
                <span>📍 ${escapeHtml(s.city)}</span>
                <span>· ${escapeHtml(s.guide_type)}</span>
              </span>
              ${s.reason ? `<span class="suggestion-card__reason">${escapeHtml(s.reason)}</span>` : ''}
            </button>
          </li>
        `).join('') || '<li class="muted">Aucune suggestion.</li>';
        bindSuggestionCards();
      } catch (err) {
        alert(err.message);
      } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = prev;
      }
    });
  }

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
});
