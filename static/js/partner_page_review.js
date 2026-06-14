document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('partner-review');
  if (!root) return;

  const stateUrl = root.dataset.stateUrl;
  const applyUrl = root.dataset.applyUrl;
  const overlay = document.getElementById('partner-review-overlay');
  const overlayPhase = document.getElementById('partner-review-overlay-phase');
  const overlayHint = document.getElementById('partner-review-overlay-hint');
  const jobPhaseEl = document.getElementById('partner-review-phase');

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showOverlay(phase, hint) {
    if (!overlay) return;
    overlay.hidden = false;
    root.classList.add('is-busy');
    if (overlayPhase) overlayPhase.textContent = phase || 'Traitement en cours…';
    if (overlayHint) overlayHint.textContent = hint || '';
  }

  function hideOverlay() {
    if (!overlay) return;
    overlay.hidden = true;
    root.classList.remove('is-busy');
  }

  async function runPhaseSequence(phases, hint) {
    showOverlay(phases[0] || 'Traitement en cours…', hint);
    for (let i = 0; i < phases.length; i += 1) {
      if (overlayPhase) overlayPhase.textContent = phases[i];
      // eslint-disable-next-line no-await-in-loop
      await sleep(i === 0 ? 200 : 550);
    }
  }

  /* ── Corrections IA (sans rechargement) ── */
  const fixesRoot = document.getElementById('partner-fixes-root');
  const fixesList = document.getElementById('partner-fixes-list');
  const fixesCount = document.getElementById('partner-fixes-count');
  const fixesFeedback = document.getElementById('partner-fixes-feedback');
  const fixesDone = document.getElementById('partner-fixes-done');
  const applyAllBtn = document.getElementById('partner-fixes-apply-all');

  function setFeedback(text, ok) {
    if (!fixesFeedback) return;
    fixesFeedback.hidden = !text;
    fixesFeedback.textContent = text || '';
    fixesFeedback.classList.toggle('flash--success', Boolean(ok));
    fixesFeedback.classList.toggle('flash--error', Boolean(text && !ok));
  }

  function updateFixesCount(n) {
    if (fixesCount) fixesCount.textContent = String(n);
    if (applyAllBtn) applyAllBtn.hidden = n <= 0;
  }

  function removeFixCards(ids) {
    if (!fixesList) return;
    ids.forEach((id) => {
      const card = fixesList.querySelector(`[data-fix-id="${CSS.escape(id)}"]`);
      if (card) {
        card.classList.add('is-removing');
        setTimeout(() => card.remove(), 320);
      }
    });
  }

  function checkFixesEmpty() {
    const remaining = fixesList ? fixesList.querySelectorAll('.partner-fix-card').length : 0;
    updateFixesCount(remaining);
    if (remaining === 0 && fixesDone) {
      fixesDone.hidden = false;
      if (fixesRoot) fixesRoot.classList.add('is-complete');
      const retryBtn = document.getElementById('partner-review-retry-btn');
      const actions = document.getElementById('partner-review-actions');
      if (retryBtn) {
        retryBtn.classList.add('is-highlight');
        retryBtn.focus({ preventScroll: true });
      }
      if (actions) {
        actions.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }

  function bindFixButtons() {
    if (!fixesRoot || !applyUrl) return;

    fixesRoot.querySelectorAll('.partner-fix-apply-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const fixId = btn.dataset.fixId;
        const card = btn.closest('.partner-fix-card');
        const label = card?.querySelector('h4')?.textContent?.trim() || 'correction';
        applyFixes({ fixId, label, applyAll: false });
      });
    });

    if (applyAllBtn) {
      applyAllBtn.addEventListener('click', () => {
        const cards = fixesList ? Array.from(fixesList.querySelectorAll('.partner-fix-card')) : [];
        const labels = cards.map((c) => c.querySelector('h4')?.textContent?.trim() || 'correction');
        applyFixes({ applyAll: true, labels });
      });
    }
  }

  async function relaunchVerification() {
    const retryUrl = root.dataset.retryUrl;
    if (!retryUrl || root.classList.contains('is-busy')) return;
    showOverlay(
      'Relance de la vérification IA…',
      'Analyse du brouillon corrigé — patientez 30 à 120 s.',
    );
    try {
      const res = await fetch(retryUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (res.redirected) {
        window.location.href = res.url;
        return;
      }
      if (res.ok) {
        window.location.reload();
        return;
      }
      throw new Error('Impossible de relancer la vérification.');
    } catch (err) {
      hideOverlay();
      setFeedback(err.message || 'Erreur lors de la relance.', false);
      const retryBtn = document.getElementById('partner-review-retry-btn');
      if (retryBtn) retryBtn.classList.add('is-highlight');
    }
  }

  async function applyFixes({ fixId, label, labels, applyAll }) {
    if (!applyUrl || root.classList.contains('is-busy')) return;

    const phaseLabels = applyAll
      ? (labels || [])
      : [label || 'correction'];

    const phases = phaseLabels.map((l) => `Application de « ${l} »…`);
    phases.push('Enregistrement du brouillon…');

    setFeedback('');
    root.querySelectorAll('.partner-fix-apply-btn, #partner-fixes-apply-all').forEach((b) => {
      b.disabled = true;
    });

    try {
      await runPhaseSequence(
        phases,
        applyAll
          ? 'Mise à jour de votre brouillon — ne fermez pas cette page.'
          : 'Mise à jour en cours…',
      );

      const res = await fetch(applyUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fix_id: fixId || '',
          apply_all: Boolean(applyAll),
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || 'Impossible d\'appliquer la correction.');
      }

      if (overlayPhase) overlayPhase.textContent = 'Corrections enregistrées ✓';
      await sleep(450);

      removeFixCards(data.applied_ids || []);
      setFeedback(
        `${data.applied_count} correction(s) appliquée(s) — brouillon mis à jour.`,
        true,
      );

      setTimeout(checkFixesEmpty, 350);

      if ((data.remaining_fixes || []).length === 0 && fixesDone) {
        fixesDone.hidden = false;
        if (fixesRoot) fixesRoot.classList.add('is-complete');
      }

      if (data.should_relaunch) {
        await sleep(600);
        await relaunchVerification();
      }
    } catch (err) {
      setFeedback(err.message || 'Erreur lors de l\'application.', false);
    } finally {
      hideOverlay();
      root.querySelectorAll('.partner-fix-apply-btn, #partner-fixes-apply-all').forEach((b) => {
        b.disabled = false;
      });
    }
  }

  if (fixesRoot && applyUrl) {
    bindFixButtons();
  }

  /* ── Polling vérification IA (loader génération) ── */
  if (stateUrl && jobPhaseEl) {
    let polls = 0;
    const maxPolls = 80;

    async function pollJob() {
      polls += 1;
      try {
        const res = await fetch(stateUrl, {
          credentials: 'same-origin',
          headers: { Accept: 'application/json' },
        });
        const data = await res.json();
        const job = data.job || {};
        if (job.phase) jobPhaseEl.textContent = job.phase;

        if (data.page_ready || job.status === 'done' || job.status === 'error') {
          window.location.reload();
          return;
        }
        if (polls >= maxPolls) {
          window.location.reload();
          return;
        }
      } catch (e) {
        /* retry */
      }
      setTimeout(pollJob, 2500);
    }

    pollJob();
  }
});
