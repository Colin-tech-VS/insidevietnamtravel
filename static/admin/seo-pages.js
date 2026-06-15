document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('seo-form-ai');
  const overlay = document.getElementById('ai-loader');
  const loaderText = document.getElementById('ai-loader-text');
  const loaderBar = document.getElementById('ai-loader-bar');
  const loaderElapsed = document.getElementById('ai-loader-elapsed');

  let elapsedTimer = null;
  let loaderStart = 0;
  let barPct = 5;

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

  function fmtElapsed(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
  }

  function startLoader(text) {
    if (!overlay) return;
    overlay.hidden = false;
    if (loaderText) loaderText.textContent = text || 'Préparation…';
    barPct = 8;
    if (loaderBar) loaderBar.style.width = `${barPct}%`;
    loaderStart = Date.now();
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = setInterval(() => {
      if (loaderElapsed) loaderElapsed.textContent = fmtElapsed(Date.now() - loaderStart);
      barPct = Math.min(92, barPct + 0.8);
      if (loaderBar) loaderBar.style.width = `${barPct}%`;
    }, 1000);
  }

  function stopLoader() {
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = null;
    if (overlay) overlay.hidden = true;
    if (loaderBar) loaderBar.style.width = '100%';
  }

  async function pollStatus() {
    const res = await fetch('/admin/api/seo-pages/draft-status', { credentials: 'same-origin' });
    const data = await res.json();
    if (data.phase && loaderText) loaderText.textContent = data.phase;
    if (data.status === 'running') {
      setTimeout(pollStatus, 1500);
      return;
    }
    stopLoader();
    if (data.status === 'error') {
      alert(data.error || 'Erreur de génération');
      return;
    }
    window.location.reload();
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const topic = (document.getElementById('topic')?.value || '').trim();
      const keywords = (document.getElementById('keywords')?.value || '').trim();
      const city = (document.getElementById('city')?.value || '').trim();
      const pageType = (document.getElementById('page_type')?.value || 'landing').trim();
      if (!topic && !keywords) {
        alert('Indiquez un sujet ou des mots-clés.');
        return;
      }
      startLoader('Analyse des mots-clés SEO…');
      try {
        const res = await fetch('/admin/api/seo-pages/generate', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic, keywords, city, page_type: pageType }),
        });
        const data = await res.json();
        if (!data.ok) {
          stopLoader();
          alert(data.error || 'Erreur');
          return;
        }
        pollStatus();
      } catch (err) {
        stopLoader();
        alert(err.message || 'Erreur réseau');
      }
    });
  }
});
