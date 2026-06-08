document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('newsletter-form-ai');
  const overlay = document.getElementById('ai-loader');
  const loaderText = document.getElementById('ai-loader-text');

  const PHRASES = [
    'Analyse du sujet newsletter…',
    'Ciblage voyageurs Vietnam…',
    'Rédaction de l\'objet accrocheur…',
    'Optimisation du preheader…',
    'Rédaction du corps de l\'email…',
    'Ajout des conseils pratiques…',
    'Intégration du call-to-action…',
    'Polissage du ton éditorial…',
    'Finalisation…',
  ];

  let phraseTimer = null;
  let idx = 0;

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
      if (target === 'manual' && window.tinymce) {
        setTimeout(() => tinymce.editors.forEach((ed) => ed.fire('ResizeEditor')), 80);
      }
    });
  });

  function startLoader() {
    if (!overlay) return;
    idx = 0;
    overlay.hidden = false;
    if (loaderText) loaderText.textContent = PHRASES[0];
    phraseTimer = setInterval(() => {
      idx = (idx + 1) % PHRASES.length;
      if (loaderText) loaderText.textContent = PHRASES[idx];
    }, 2400);
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

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const topic = document.getElementById('nl-topic')?.value?.trim();
      const notes = document.getElementById('nl-notes')?.value?.trim() || '';
      const emailType = form.querySelector('input[name="email_type"]:checked')?.value;
      if (!topic) {
        form.reportValidity();
        return;
      }

      const btn = form.querySelector('.btn-generate');
      if (btn) btn.disabled = true;
      startLoader();

      try {
        const res = await fetch('/admin/api/newsletter/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ topic, email_type: emailType, notes }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || 'Erreur génération');
        await pollDraft('/admin/api/newsletter/draft-status');
        window.location.reload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  }
});
