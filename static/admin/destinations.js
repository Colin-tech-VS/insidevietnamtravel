document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('dest-form-ai');
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

  const PHRASES = [
    'Analyse de la destination Vietnam…',
    'Rédaction vue d\'ensemble SEO…',
    'Sélection des incontournables…',
    'Recherche hôtels et budgets…',
    'Activités et tours affiliés…',
    'Conseils pratiques locaux…',
    'Optimisation meta title / description…',
    'Génération image Vietnam unique…',
    'Export WebP optimisé…',
    'Finalisation de la page…',
  ];

  let phraseTimer = null;
  let idx = 0;

  function startLoader() {
    if (!overlay) return;
    idx = 0;
    overlay.hidden = false;
    if (loaderText) loaderText.textContent = PHRASES[0];
    phraseTimer = setInterval(() => {
      idx = (idx + 1) % PHRASES.length;
      if (loaderText) loaderText.textContent = PHRASES[idx];
    }, 2800);
  }

  function stopLoader() {
    if (phraseTimer) clearInterval(phraseTimer);
    if (overlay) overlay.hidden = true;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Génération serveur en tâche de fond : on interroge le statut jusqu'à done/error.
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
        continue;
      }
      if (st.status === 'done') return;
      if (st.status === 'error') throw new Error(st.error || 'Échec de la génération.');
      if (st.status === 'missing') throw new Error('Session expirée — relancez la génération.');
    }
    throw new Error('Génération anormalement longue. Rafraîchissez la page dans un instant.');
  }

  // Affiche l'aperçu dynamiquement, sans recharger la page (comme les onglets).
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
        stopLoader();
        slot.querySelector('.draft-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }
    } catch (e) { /* repli ci-dessous */ }
    window.location.reload();
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const city = document.getElementById('dest-city')?.value;
      const notes = document.getElementById('dest-notes')?.value?.trim() || '';
      if (!city) {
        form.reportValidity();
        return;
      }

      const btn = form.querySelector('.btn-generate');
      if (btn) btn.disabled = true;
      startLoader();

      try {
        const res = await fetch('/admin/api/destinations/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ city, notes }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || 'Erreur génération');
        await pollDraft('/admin/api/destinations/draft-status');
        await softReload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  }
});
