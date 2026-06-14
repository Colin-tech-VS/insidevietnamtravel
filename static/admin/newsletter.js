document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('newsletter-form-ai');
  const overlay = document.getElementById('ai-loader');
  const loaderText = document.getElementById('ai-loader-text');
  const loaderBar = document.getElementById('ai-loader-bar');
  const loaderElapsed = document.getElementById('ai-loader-elapsed');

  let elapsedTimer = null;
  let loaderStart = 0;
  let barPct = 0;
  let barFloor = 0;

  function fmtElapsed(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

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
      if (target === 'manual' && window.tinymce) {
        setTimeout(() => tinymce.editors.forEach((ed) => ed.fire('ResizeEditor')), 80);
      }
    });
  });

  // Le texte du modal reflète l'étape RÉELLE renvoyée par le serveur (phase du job),
  // pas une liste de phrases qui défilent au hasard sur un minuteur.
  function startLoader(initialText) {
    if (!overlay) return;
    overlay.hidden = false;
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
    if (overlay) overlay.hidden = true;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Génération serveur en tâche de fond : on interroge le statut jusqu'à done/error.
  // On NE coupe PAS tant que le serveur signale une progression (status running) :
  // une génération sur palier gratuit peut légitimement durer plusieurs minutes. On
  // n'abandonne qu'en cas de perte de contact prolongée (idleMs) ou au-delà d'un
  // plafond absolu de sécurité (hardCapMs).
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
      const topic = document.getElementById('nl-topic')?.value?.trim();
      const notes = document.getElementById('nl-notes')?.value?.trim() || '';
      const partnerName = document.getElementById('nl-partner-name')?.value?.trim() || '';
      const recipientEmail = document.getElementById('nl-recipient-email')?.value?.trim() || '';
      const partnerId = document.getElementById('nl-partner-id')?.value?.trim() || '';
      const emailType = form.querySelector('input[name="email_type"]:checked')?.value;
      if (!topic) {
        form.reportValidity();
        return;
      }

      const btn = form.querySelector('.btn-generate');
      if (btn) btn.disabled = true;
      startLoader('Connexion au moteur IA…');

      try {
        const res = await fetch('/admin/api/newsletter/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            topic,
            email_type: emailType,
            notes,
            partner_name: partnerName,
            recipient_email: recipientEmail,
            partner_id: partnerId,
          }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || 'Erreur génération');
        await pollDraft('/admin/api/newsletter/draft-status');
        await softReload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  }

  // Depuis Partenariats : ?prefill=1&auto_generate=1&email_type=partenariat…
  // → pré-remplit le formulaire (prefill.js) puis lance la génération IA ici.
  (function maybeAutoGeneratePartnerEmail() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('prefill') !== '1' || params.get('auto_generate') !== '1') return;
    if (!form) return;

    const topic = document.getElementById('nl-topic')?.value?.trim();
    const emailType = form.querySelector('input[name="email_type"]:checked')?.value;
    const btn = form.querySelector('.btn-generate');
    if (!topic || emailType !== 'partenariat' || !btn || btn.disabled) return;

    const partnerName = document.getElementById('nl-partner-name')?.value?.trim();
    document.querySelector('.content-tab[data-tab="ai"]')?.click();

    const notice = document.createElement('p');
    notice.className = 'flash flash--success';
    notice.textContent = partnerName
      ? `🤝 Génération IA de l'email partenariat pour ${partnerName}…`
      : '🤝 Génération IA de l\'email partenariat…';
    form.parentNode?.insertBefore(notice, form);

    history.replaceState({}, '', window.location.pathname);
    setTimeout(() => form.requestSubmit(btn), 120);
  })();
});
