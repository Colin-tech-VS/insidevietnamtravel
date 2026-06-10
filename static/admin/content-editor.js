/**
 * Édition des contenus publiés : amélioration IA + photo de couverture (jobs async).
 */
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('ai-loader');
  const loaderText = document.getElementById('ai-loader-text');
  const loaderBar = document.getElementById('ai-loader-bar');
  const loaderElapsed = document.getElementById('ai-loader-elapsed');
  const statusUrl = '/admin/api/content/job-status';

  let elapsedTimer = null;
  let pollTimer = null;
  let loaderStart = 0;
  let barPct = 5;
  let barFloor = 5;

  function fmtElapsed(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
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

  function progressForPhase(phase) {
    const p = (phase || '').toLowerCase();
    if (p.includes('connexion') || p.includes('traitement')) return 10;
    if (p.includes('amélioration') || p.includes('réécriture')) return 35;
    if (p.includes('recherche') && p.includes('image')) return 40;
    if (p.includes('téléchargement') || p.includes('image')) return 70;
    if (p.includes('finalisation')) return 90;
    return null;
  }

  function startLoader(text) {
    if (!overlay) return;
    overlay.hidden = false;
    if (loaderText) loaderText.textContent = text || 'Traitement…';
    barPct = 8;
    barFloor = 8;
    renderBar();
    loaderStart = Date.now();
    if (loaderElapsed) loaderElapsed.textContent = '0:00';
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = setInterval(() => {
      if (loaderElapsed) loaderElapsed.textContent = fmtElapsed(Date.now() - loaderStart);
      const ceiling = Math.min(94, barFloor + 10);
      if (barPct < ceiling) {
        barPct = Math.min(ceiling, barPct + 0.5);
        renderBar();
      }
    }, 1000);
  }

  function stopLoader() {
    if (elapsedTimer) {
      clearInterval(elapsedTimer);
      elapsedTimer = null;
    }
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    barPct = 100;
    renderBar();
    if (overlay) overlay.hidden = true;
  }

  function pollJob(onDone) {
    function tick() {
      fetch(statusUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then((r) => r.json())
        .then((st) => {
          if (st.phase && loaderText) loaderText.textContent = st.phase;
          setBarFloor(progressForPhase(st.phase));
          if (st.status === 'running') {
            pollTimer = setTimeout(tick, 2000);
            return;
          }
          stopLoader();
          if (st.status === 'done') {
            const msg = (st.result && st.result.message) || 'Modification enregistrée.';
            alert(msg);
            if (onDone) onDone(st);
            else window.location.reload();
          } else if (st.status === 'error') {
            alert('Erreur : ' + (st.error || 'échec du traitement'));
          } else {
            alert('Session expirée — réessayez.');
          }
        })
        .catch(() => {
          pollTimer = setTimeout(tick, 3000);
        });
    }
    pollTimer = setTimeout(tick, 1500);
  }

  function postJson(url, body) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => r.json().then((data) => ({ ok: r.ok, data })));
  }

  document.querySelectorAll('.content-improve-form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const slug = form.dataset.slug;
      const target = form.dataset.target || 'article';
      const instructions = (form.querySelector('[name="instructions"]') || {}).value || '';
      if (!instructions.trim()) {
        alert('Décrivez ce que l\'IA doit améliorer.');
        return;
      }
      const url = target === 'destination'
        ? `/admin/api/content/destination/${encodeURIComponent(slug)}/improve`
        : `/admin/api/content/article/${encodeURIComponent(slug)}/improve`;
      startLoader('Amélioration IA en cours…');
      postJson(url, { instructions: instructions.trim() }).then(({ ok, data }) => {
        if (!ok || !data.ok) {
          stopLoader();
          alert(data.error || 'Impossible de lancer l\'amélioration.');
          return;
        }
        pollJob();
      }).catch(() => {
        stopLoader();
        alert('Erreur réseau.');
      });
    });
  });

  document.querySelectorAll('.content-image-form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const slug = form.dataset.slug;
      const target = form.dataset.target || 'article';
      const image_url = (form.querySelector('[name="image_url"]') || {}).value || '';
      const query = (form.querySelector('[name="query"]') || {}).value || '';
      const alt = (form.querySelector('[name="alt"]') || {}).value || '';
      if (!image_url.trim() && !query.trim()) {
        alert('Indiquez une URL d\'image ou des mots-clés Pixabay.');
        return;
      }
      const url = target === 'destination'
        ? `/admin/api/content/destination/${encodeURIComponent(slug)}/image`
        : `/admin/api/content/article/${encodeURIComponent(slug)}/image`;
      startLoader('Mise à jour de la photo…');
      postJson(url, {
        image_url: image_url.trim(),
        query: query.trim(),
        alt: alt.trim(),
      }).then(({ ok, data }) => {
        if (!ok || !data.ok) {
          stopLoader();
          alert(data.error || 'Impossible de mettre à jour l\'image.');
          return;
        }
        pollJob();
      }).catch(() => {
        stopLoader();
        alert('Erreur réseau.');
      });
    });
  });
});
