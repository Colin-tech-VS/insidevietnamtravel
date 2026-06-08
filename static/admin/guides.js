document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('guide-form-ai');
  const topicInput = document.getElementById('topic');
  const citySelect = document.getElementById('city');
  const overlay = document.getElementById('ai-loader');
  const loaderText = document.getElementById('ai-loader-text');

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

  const GENERATE_PHRASES = [
    'Analyse du sujet et de la destination…',
    'Recherche des mots-clés SEO Vietnam…',
    'Ciblage voyageurs français en préparation…',
    'Rédaction de l\'introduction optimisée…',
    'Structuration H2 / H3 pour Google…',
    'Rédaction des conseils pratiques…',
    'Ajout du budget et fourchettes de prix…',
    'Création de la section FAQ…',
    'Optimisation meta description…',
    'Vérification longueur et sémantique…',
    'Génération de l\'image Vietnam…',
    'Conversion WebP pour chargement rapide…',
    'Finalisation de l\'article…',
  ];

  const IMPROVE_PHRASES = [
    'Analyse du brouillon existant…',
    'Renforcement des mots-clés SEO…',
    'Enrichissement des sections pratiques…',
    'Amélioration de la FAQ…',
    'Mise à jour de l\'image si nécessaire…',
    'Polissage final du contenu…',
  ];

  let phraseTimer = null;
  let phraseIndex = 0;

  function startLoader(phrases) {
    if (!overlay) return;
    phraseIndex = 0;
    overlay.hidden = false;
    overlay.setAttribute('aria-busy', 'true');
    if (loaderText) loaderText.textContent = phrases[0];
    phraseTimer = setInterval(() => {
      phraseIndex = (phraseIndex + 1) % phrases.length;
      if (loaderText) loaderText.textContent = phrases[phraseIndex];
    }, 2800);
  }

  function stopLoader() {
    if (phraseTimer) clearInterval(phraseTimer);
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
  async function pollDraft(statusUrl, maxMs = 360000) {
    const start = Date.now();
    while (Date.now() - start < maxMs) {
      await sleep(2500);
      let st;
      try {
        const res = await fetch(statusUrl, {
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' },
        });
        st = await res.json();
      } catch (e) {
        continue; // micro-coupure réseau : on retente
      }
      if (st.status === 'done') return;
      if (st.status === 'error') throw new Error(st.error || 'Échec de la génération.');
      if (st.status === 'missing') throw new Error('Session expirée — relancez la génération.');
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
      startLoader(GENERATE_PHRASES);

      try {
        await postJson('/admin/api/guides/generate', {
          city,
          topic,
          guide_type: guideType,
        });
        await pollDraft('/admin/api/guides/draft-status');
        window.location.reload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  }

  document.querySelectorAll('.draft-action-form--improve').forEach((improveForm) => {
    improveForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const instructions = improveForm.querySelector('[name="instructions"]')?.value
        || 'Améliore le SEO pour voyageurs préparant un voyage au Vietnam.';
      const btn = improveForm.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      startLoader(IMPROVE_PHRASES);

      try {
        await postJson('/admin/api/guides/improve', { instructions });
        await pollDraft('/admin/api/guides/draft-status');
        window.location.reload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  });

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
