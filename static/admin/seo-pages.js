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
  let matrixRows = [];

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

  function startLoader(title, text) {
    if (!overlay) return;
    overlay.hidden = false;
    if (loaderTitle) loaderTitle.textContent = title || 'Génération IA';
    if (loaderText) loaderText.textContent = text || 'Préparation…';
    barPct = 8;
    if (loaderBar) loaderBar.style.width = `${barPct}%`;
    loaderStart = Date.now();
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = setInterval(() => {
      if (loaderElapsed) loaderElapsed.textContent = fmtElapsed(Date.now() - loaderStart);
      barPct = Math.min(94, barPct + 0.5);
      if (loaderBar) loaderBar.style.width = `${barPct}%`;
    }, 1000);
  }

  function stopLoader() {
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = null;
    if (overlay) overlay.hidden = true;
    if (loaderBar) loaderBar.style.width = '100%';
  }

  async function pollStatus(url, onDone) {
    const data = await fetch(url, { credentials: 'same-origin' }).then((r) => r.json());
    if (data.phase && loaderText) loaderText.textContent = data.phase;
    if (data.status === 'running') {
      setTimeout(() => pollStatus(url, onDone), 2000);
      return;
    }
    stopLoader();
    if (data.status === 'error') {
      alert(data.error || 'Erreur de génération');
      return;
    }
    if (onDone) onDone(data);
    else window.location.reload();
  }

  function renderMatrix() {
    const panel = document.getElementById('matrix-panel');
    const tbody = document.getElementById('matrix-tbody');
    const countEl = document.getElementById('matrix-count');
    if (!tbody || !panel) return;
    if (!matrixRows.length) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    const selected = matrixRows.filter((r) => r.selected && !r.duplicate).length;
    if (countEl) countEl.textContent = `(${selected} sélectionnée(s) / ${matrixRows.length})`;
    tbody.innerHTML = matrixRows.map((row, i) => `
      <tr class="${row.duplicate ? 'matrix-row--dup' : ''}">
        <td><input type="checkbox" data-matrix-idx="${i}" ${row.selected && !row.duplicate ? 'checked' : ''} ${row.duplicate ? 'disabled' : ''}></td>
        <td><span class="suggestion-card__priority suggestion-card__priority--${escapeHtml(row.priority || 'moyenne')}">${escapeHtml(row.priority || 'moyenne')}</span></td>
        <td>${escapeHtml(row.topic)}${row.duplicate ? ' <span class="muted">(doublon)</span>' : ''}</td>
        <td class="matrix-kw">${escapeHtml((row.keywords || []).slice(0, 5).join(' · '))}</td>
        <td>${escapeHtml(row.city || '—')}</td>
      </tr>
    `).join('');
    tbody.querySelectorAll('input[type=checkbox]').forEach((cb) => {
      cb.addEventListener('change', () => {
        const idx = parseInt(cb.dataset.matrixIdx, 10);
        if (matrixRows[idx]) matrixRows[idx].selected = cb.checked;
        renderMatrix();
      });
    });
  }

  function setMatrix(rows) {
    matrixRows = rows || [];
    renderMatrix();
    document.querySelector('.content-tab[data-tab="matrix"]')?.click();
  }

  function addToMatrix(rows) {
    const existing = new Set(matrixRows.map((r) => (r.topic || '').toLowerCase().slice(0, 40)));
    for (const row of rows) {
      const key = (row.topic || '').toLowerCase().slice(0, 40);
      if (key && !existing.has(key)) {
        existing.add(key);
        matrixRows.push({ ...row, id: row.id || `s-${Date.now()}`, selected: !row.duplicate });
      }
    }
    renderMatrix();
  }

  document.getElementById('btn-matrix-build')?.addEventListener('click', async () => {
    const data = await postJson('/admin/api/seo-pages/matrix/build', {
      axis_a: document.getElementById('axis_a')?.value || '',
      axis_b: document.getElementById('axis_b')?.value || '',
      city: document.getElementById('matrix_city')?.value || '',
      page_type: document.getElementById('matrix_page_type')?.value || 'landing',
    });
    if (!data.ok) { alert(data.error || 'Erreur'); return; }
    setMatrix(data.rows);
  });

  document.getElementById('btn-matrix-ai')?.addEventListener('click', async () => {
    startLoader('Matrice IA', 'Analyse des clusters SEO…');
    try {
      const data = await postJson('/admin/api/seo-pages/matrix/generate', {
        brief: document.getElementById('matrix_brief')?.value || '',
        count: parseInt(document.getElementById('matrix_ai_count')?.value || '10', 10),
        city: document.getElementById('matrix_ai_city')?.value || '',
      });
      stopLoader();
      if (!data.ok) { alert(data.error || 'Erreur'); return; }
      setMatrix(data.rows);
    } catch (e) {
      stopLoader();
      alert(e.message || 'Erreur réseau');
    }
  });

  document.getElementById('matrix-select-all')?.addEventListener('change', (e) => {
    const on = e.target.checked;
    matrixRows.forEach((r) => { if (!r.duplicate) r.selected = on; });
    renderMatrix();
  });

  document.getElementById('btn-batch-generate')?.addEventListener('click', async () => {
    const selected = matrixRows.filter((r) => r.selected && !r.duplicate);
    if (!selected.length) { alert('Sélectionnez au moins une ligne.'); return; }
    if (!confirm(`Générer ${selected.length} page(s) SEO (objectif maximal) ? Cela peut prendre plusieurs minutes.`)) return;
    startLoader(`Lot SEO (${selected.length} pages)`, 'Page 1 — rédaction SEO maximale…');
    try {
      const data = await postJson('/admin/api/seo-pages/batch-generate', { rows: selected });
      if (!data.ok) { stopLoader(); alert(data.error || 'Erreur'); return; }
      pollStatus('/admin/api/seo-pages/batch-status');
    } catch (e) {
      stopLoader();
      alert(e.message || 'Erreur');
    }
  });

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const topic = (document.getElementById('topic')?.value || '').trim();
      const keywords = (document.getElementById('keywords')?.value || '').trim();
      const city = (document.getElementById('city')?.value || '').trim();
      const pageType = (document.getElementById('page_type')?.value || 'landing').trim();
      if (!topic && !keywords) { alert('Sujet ou mots-clés requis.'); return; }
      startLoader('Page SEO', 'Rédaction SEO maximale…');
      try {
        const data = await postJson('/admin/api/seo-pages/generate', { topic, keywords, city, page_type: pageType });
        if (!data.ok) { stopLoader(); alert(data.error || 'Erreur'); return; }
        pollStatus('/admin/api/seo-pages/draft-status');
      } catch (err) {
        stopLoader();
        alert(err.message || 'Erreur réseau');
      }
    });
  }

  function fillSinglePage(card) {
    document.getElementById('topic').value = card.dataset.topic || '';
    document.getElementById('keywords').value = card.dataset.keywords || '';
    const city = card.dataset.city || '';
    const citySel = document.getElementById('city');
    if (citySel && city) citySel.value = city;
    const type = card.dataset.type || 'landing';
    const typeSel = document.getElementById('page_type');
    if (typeSel) typeSel.value = type;
    document.querySelector('.content-tab[data-tab="ai"]')?.click();
  }

  function suggestionToRow(card) {
    return {
      id: `sg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      topic: card.dataset.topic || '',
      keywords: (card.dataset.keywords || '').split(',').map((k) => k.trim()).filter(Boolean),
      city: card.dataset.city || '',
      page_type: card.dataset.type || 'landing',
      priority: 'haute',
      reason: 'Proposition SEO',
      selected: true,
    };
  }

  document.querySelectorAll('.seo-suggestion-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      if (e.shiftKey) {
        addToMatrix([suggestionToRow(card)]);
        return;
      }
      fillSinglePage(card);
    });
  });

  document.getElementById('btn-suggestions-to-matrix')?.addEventListener('click', () => {
    const rows = [...document.querySelectorAll('.seo-suggestion-card')].map(suggestionToRow);
    addToMatrix(rows);
  });

  document.getElementById('refresh-seo-suggestions')?.addEventListener('click', async () => {
    const btn = document.getElementById('refresh-seo-suggestions');
    if (btn) btn.disabled = true;
    try {
      const data = await postJson('/admin/api/seo-pages/suggestions', {});
      const list = document.getElementById('seo-suggestions-list');
      if (!data.ok || !list) { alert(data.error || 'Erreur'); return; }
      list.innerHTML = (data.suggestions || []).map((s) => `
        <li>
          <button type="button" class="suggestion-card seo-suggestion-card"
            data-topic="${escapeHtml(s.topic)}"
            data-keywords="${escapeHtml((s.keywords || []).join(', '))}"
            data-city="${escapeHtml(s.city || '')}"
            data-type="${escapeHtml(s.page_type || 'landing')}">
            <span class="suggestion-card__priority suggestion-card__priority--${escapeHtml(s.priority || 'moyenne')}">${escapeHtml(s.priority || 'moyenne')}</span>
            <span class="suggestion-card__topic">${escapeHtml(s.topic)}</span>
            <span class="suggestion-card__meta">
              ${s.volume_hint ? `<span>📈 ${escapeHtml(s.volume_hint)}</span>` : ''}
              ${s.city ? `<span>📍 ${escapeHtml(s.city)}</span>` : ''}
            </span>
            ${s.reason ? `<span class="suggestion-card__reason">${escapeHtml(s.reason)}</span>` : ''}
            <span class="suggestion-card__kw muted small">${escapeHtml((s.keywords || []).slice(0, 4).join(' · '))}</span>
          </button>
        </li>
      `).join('') || '<li class="muted">Aucune proposition.</li>';
      list.querySelectorAll('.seo-suggestion-card').forEach((card) => {
        card.addEventListener('click', (e) => {
          if (e.shiftKey) { addToMatrix([suggestionToRow(card)]); return; }
          fillSinglePage(card);
        });
      });
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  const params = new URLSearchParams(window.location.search);
  if (params.get('topic')) document.querySelector('.content-tab[data-tab="ai"]')?.click();
});
