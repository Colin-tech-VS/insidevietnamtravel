document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('ai-loader');
  const loaderTitle = document.getElementById('ai-loader-title');
  const loaderText = document.getElementById('ai-loader-text');
  const loaderBar = document.getElementById('ai-loader-bar');
  const loaderElapsed = document.getElementById('ai-loader-elapsed');
  const form = document.getElementById('seo-form-ai');

  let elapsedTimer = null;
  let loaderStart = 0;
  let barPct = 5;
  let queueRows = [];

  function escapeHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  function fmtElapsed(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
  }

  function startLoader(title, text) {
    if (!overlay) return;
    overlay.hidden = false;
    if (loaderTitle) loaderTitle.textContent = title || 'Génération en cours';
    if (loaderText) loaderText.textContent = text || "L'IA rédige la page…";
    barPct = 8;
    if (loaderBar) loaderBar.style.width = `${barPct}%`;
    loaderStart = Date.now();
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = setInterval(() => {
      if (loaderElapsed) loaderElapsed.textContent = fmtElapsed(Date.now() - loaderStart);
      barPct = Math.min(94, barPct + 0.4);
      if (loaderBar) loaderBar.style.width = `${barPct}%`;
    }, 1000);
  }

  function stopLoader() {
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = null;
    if (overlay) overlay.hidden = true;
    if (loaderBar) loaderBar.style.width = '100%';
  }

  async function pollStatus(url) {
    const data = await fetch(url, { credentials: 'same-origin' }).then((r) => r.json());
    if (data.phase && loaderText) loaderText.textContent = data.phase;
    if (data.status === 'running') {
      setTimeout(() => pollStatus(url), 2000);
      return;
    }
    stopLoader();
    if (data.status === 'error') {
      alert(data.error || 'Erreur de génération');
      return;
    }
    window.location.reload();
  }

  function rowFromCard(el) {
    return {
      topic: el.dataset.topic || '',
      keywords: (el.dataset.keywords || '').split(',').map((k) => k.trim()).filter(Boolean),
      city: el.dataset.city || '',
      page_type: el.dataset.type || 'landing',
      selected: true,
    };
  }

  async function generateOne({ topic, keywords, city }) {
    const t = (topic || '').trim();
    const k = (keywords || '').trim();
    if (!t && !k) {
      alert('Indiquez un sujet ou des mots-clés.');
      return;
    }
    startLoader('1 page SEO', "L'IA rédige la page…");
    try {
      const data = await postJson('/admin/api/seo-pages/generate', {
        topic: t,
        keywords: k,
        city: (city || '').trim(),
        page_type: 'landing',
      });
      if (!data.ok) {
        stopLoader();
        alert(data.error || 'Erreur');
        return;
      }
      pollStatus('/admin/api/seo-pages/draft-status');
    } catch (e) {
      stopLoader();
      alert(e.message || 'Erreur réseau');
    }
  }

  async function generateBatch(rows) {
    const selected = rows.filter((r) => r.selected !== false && !r.duplicate);
    if (!selected.length) {
      alert('Sélectionnez au moins une page.');
      return;
    }
    const n = selected.length;
    if (!confirm(`Générer ${n} page(s) ? Comptez environ ${n * 2}–${n * 5} minutes.`)) return;
    startLoader(`${n} pages SEO`, 'Page 1 en cours…');
    try {
      const data = await postJson('/admin/api/seo-pages/batch-generate', { rows: selected });
      if (!data.ok) {
        stopLoader();
        alert(data.error || 'Erreur');
        return;
      }
      pollStatus('/admin/api/seo-pages/batch-status');
    } catch (e) {
      stopLoader();
      alert(e.message || 'Erreur réseau');
    }
  }

  function updateSelectedButton() {
    const btn = document.getElementById('btn-gen-selected');
    const n = document.querySelectorAll('.idea-check:checked').length;
    if (!btn) return;
    btn.disabled = n === 0;
    btn.textContent = n ? `Générer la sélection (${n})` : 'Générer la sélection';
  }

  function setQueue(rows) {
    queueRows = (rows || []).filter((r) => !r.duplicate);
    const details = document.getElementById('seo-queue-details');
    const list = document.getElementById('seo-queue-list');
    const countEl = document.getElementById('queue-count');
    if (!details || !list) return;
    if (!queueRows.length) {
      details.hidden = true;
      return;
    }
    details.hidden = false;
    details.open = true;
    if (countEl) countEl.textContent = String(queueRows.length);
    list.innerHTML = queueRows.map((r, i) => `
      <li class="seo-queue-item">
        <label><input type="checkbox" class="queue-check" data-idx="${i}" checked></label>
        <span>${escapeHtml(r.topic)}</span>
      </li>
    `).join('');
    list.querySelectorAll('.queue-check').forEach((cb) => {
      cb.addEventListener('change', () => {
        const idx = parseInt(cb.dataset.idx, 10);
        if (queueRows[idx]) queueRows[idx].selected = cb.checked;
      });
    });
    details.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function bindIdeaCard(card) {
    const genBtn = card.querySelector('.btn-gen-one');
    const check = card.querySelector('.idea-check');
    genBtn?.addEventListener('click', () => {
      const row = rowFromCard(card);
      generateOne({ topic: row.topic, keywords: row.keywords.join(', '), city: row.city });
    });
    check?.addEventListener('change', updateSelectedButton);
  }

  document.querySelectorAll('.seo-idea-card').forEach(bindIdeaCard);

  document.getElementById('btn-gen-selected')?.addEventListener('click', () => {
    const rows = [...document.querySelectorAll('.seo-idea-card')]
      .filter((c) => c.querySelector('.idea-check')?.checked)
      .map(rowFromCard);
    generateBatch(rows);
  });

  document.getElementById('btn-propose-batch')?.addEventListener('click', async () => {
    startLoader('Idées de pages', "L'IA prépare 6 sujets SEO…");
    try {
      const data = await postJson('/admin/api/seo-pages/matrix/generate', { brief: '', count: 6 });
      stopLoader();
      if (!data.ok) {
        alert(data.error || 'Erreur');
        return;
      }
      setQueue(data.rows);
    } catch (e) {
      stopLoader();
      alert(e.message || 'Erreur réseau');
    }
  });

  document.getElementById('btn-matrix-build')?.addEventListener('click', async () => {
    const data = await postJson('/admin/api/seo-pages/matrix/build', {
      axis_a: document.getElementById('axis_a')?.value || '',
      axis_b: document.getElementById('axis_b')?.value || '',
      page_type: 'landing',
    });
    if (!data.ok) {
      alert(data.error || 'Erreur');
      return;
    }
    setQueue(data.rows);
  });

  document.getElementById('btn-queue-generate')?.addEventListener('click', () => {
    generateBatch(queueRows);
  });

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      generateOne({
        topic: document.getElementById('topic')?.value,
        keywords: document.getElementById('keywords')?.value,
        city: document.getElementById('city')?.value,
      });
    });
  }

  document.getElementById('refresh-seo-suggestions')?.addEventListener('click', async () => {
    const btn = document.getElementById('refresh-seo-suggestions');
    if (btn) btn.disabled = true;
    try {
      const data = await postJson('/admin/api/seo-pages/suggestions', {});
      const list = document.getElementById('seo-suggestions-list');
      if (!data.ok || !list) {
        alert(data.error || 'Erreur');
        return;
      }
      list.innerHTML = (data.suggestions || []).map((s) => `
        <li class="seo-idea-card"
          data-topic="${escapeHtml(s.topic)}"
          data-keywords="${escapeHtml((s.keywords || []).join(', '))}"
          data-city="${escapeHtml(s.city || '')}"
          data-type="${escapeHtml(s.page_type || 'landing')}">
          <label class="seo-idea-card__check"><input type="checkbox" class="idea-check"></label>
          <div class="seo-idea-card__body">
            <span class="seo-idea-card__title">${escapeHtml(s.topic)}</span>
            ${s.city ? `<span class="seo-idea-card__meta">📍 ${escapeHtml(s.city)}</span>` : ''}
          </div>
          <button type="button" class="btn btn-primary btn-sm btn-gen-one">Générer</button>
        </li>
      `).join('') || '<li class="muted">Aucune idée pour le moment.</li>';
      list.querySelectorAll('.seo-idea-card').forEach(bindIdeaCard);
      updateSelectedButton();
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  updateSelectedButton();
});
