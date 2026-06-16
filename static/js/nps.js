(function initNpsWidget() {
  const widget = document.getElementById('nps-widget');
  if (!widget) return;

  const STORAGE_KEY = 'ivt_nps_state';
  // Une fois noté/fermé sur une page donnée, on ne re-sollicite pas avant ce délai.
  const COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000; // 30 jours

  const apiUrl = widget.dataset.apiUrl;
  const lang = widget.dataset.lang || 'fr';
  const pagePath = window.location.pathname;

  const readState = () => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {};
    } catch {
      return {};
    }
  };

  const markDone = () => {
    const state = readState();
    state[pagePath] = Date.now();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* localStorage indisponible — pas bloquant */
    }
  };

  // Déjà noté/fermé récemment sur cette page → on n'affiche rien.
  const last = readState()[pagePath];
  if (last && Date.now() - last < COOLDOWN_MS) {
    widget.remove();
    return;
  }

  const stars = Array.from(widget.querySelectorAll('.nps-widget__star'));
  const followup = document.getElementById('nps-followup');
  const commentEl = document.getElementById('nps-comment');
  const submitBtn = document.getElementById('nps-submit');
  const body = document.getElementById('nps-body');
  const thanks = document.getElementById('nps-thanks');
  const errorEl = document.getElementById('nps-error');
  const closeBtn = document.getElementById('nps-close');

  let selected = 0;

  const paint = (upto) => {
    stars.forEach((star) => {
      const val = Number(star.dataset.value);
      star.classList.toggle('is-on', val <= upto);
    });
  };

  stars.forEach((star) => {
    const val = Number(star.dataset.value);
    star.addEventListener('mouseenter', () => paint(val));
    star.addEventListener('focus', () => paint(val));
    star.addEventListener('click', () => {
      selected = val;
      paint(val);
      stars.forEach((s) => s.setAttribute('aria-checked', Number(s.dataset.value) === val ? 'true' : 'false'));
      if (followup) followup.hidden = false;
      if (commentEl) commentEl.focus();
    });
  });

  widget.querySelector('.nps-widget__stars').addEventListener('mouseleave', () => paint(selected));

  const hide = () => {
    widget.classList.add('is-hiding');
    setTimeout(() => widget.remove(), 320);
  };

  const submit = () => {
    if (!selected) return;
    if (submitBtn) submitBtn.disabled = true;
    if (errorEl) errorEl.hidden = true;

    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rating: selected,
        comment: commentEl ? commentEl.value.trim().slice(0, 500) : '',
        path: pagePath,
        lang,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('nps');
        markDone();
        if (body) body.hidden = true;
        if (thanks) thanks.hidden = false;
        setTimeout(hide, 2200);
      })
      .catch(() => {
        if (submitBtn) submitBtn.disabled = false;
        if (errorEl) errorEl.hidden = false;
      });
  };

  if (submitBtn) submitBtn.addEventListener('click', submit);

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      markDone();
      hide();
    });
  }
})();
