document.addEventListener('DOMContentLoaded', () => {
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
    if (p.includes('génération') || p.includes('rédaction')) return 25;
    if (p.includes('enrichissement')) return 55;
    if (p.includes('image')) return 80;
    if (p.includes('finalisation')) return 95;
    return null;
  }

  function renderBar() { if (loaderBar) loaderBar.style.width = `${barPct}%`; }
  function setBarFloor(pct) {
    if (pct == null) return;
    barFloor = pct;
    if (barPct < pct) { barPct = pct; renderBar(); }
  }
  function creepBar() {
    const ceiling = Math.min(94, barFloor + 12);
    if (barPct < ceiling) { barPct = Math.min(ceiling, barPct + 0.6); renderBar(); }
  }

  function startLoader(initialText) {
    if (!overlay) return;
    overlay.hidden = false;
    if (loaderText) loaderText.textContent = initialText || 'Préparation…';
    barPct = 5; barFloor = 5; renderBar();
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
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
    barPct = 100; barFloor = 100; renderBar();
    if (overlay) overlay.hidden = true;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
      lastAlive = Date.now();
      setPhase(st.phase);
    }
    throw new Error('Génération anormalement longue. Rafraîchissez la page dans un instant.');
  }

  const val = (form, name) => (form.querySelector(`[name="${name}"]`)?.value || '').trim();

  document.querySelectorAll('.rp-generate-form').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const partnerId = form.dataset.partnerId;
      const title = val(form, 'title');
      if (!title) { form.reportValidity(); return; }
      const payload = {
        partner_id: partnerId,
        title,
        price: val(form, 'price'),
        currency: val(form, 'currency') || '€',
        duration: val(form, 'duration'),
        booking_url: val(form, 'booking_url'),
        prompt: val(form, 'prompt'),
      };
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      startLoader('Connexion au moteur IA…');
      try {
        const res = await fetch('/admin/api/recommended-partners/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || 'Erreur génération');
        await pollDraft('/admin/api/recommended-partners/draft-status');
        stopLoader();
        window.location.reload();
      } catch (err) {
        stopLoader();
        alert(err.message);
        if (btn) btn.disabled = false;
      }
    });
  document.querySelectorAll('form[enctype="multipart/form-data"]').forEach((form) => {
    form.addEventListener('submit', () => {
      const hasFile = Array.from(form.querySelectorAll('input[type="file"]')).some(
        (input) => input.files && input.files.length > 0,
      );
      if (!hasFile) return;
      form.querySelectorAll('button[type="submit"]').forEach((btn) => {
        btn.disabled = true;
        if (!btn.dataset.origLabel) btn.dataset.origLabel = btn.textContent.trim();
        btn.textContent = 'Envoi en cours…';
      });
    });
  });
});
