/* ── Pop-up d'inscription newsletter ──────────────────────────────────────
 * Déclenché par exit-intent (desktop), profondeur de scroll, ou délai.
 * Anti-harcèlement : ne réapparaît pas si l'utilisateur est déjà inscrit, ou
 * s'il a fermé le pop-up récemment (cooldown). Soumission AJAX, sans rechargement.
 * Améliore aussi le formulaire du pied de page (.newsletter__form) en AJAX pour
 * que toute inscription supprime définitivement le pop-up.
 */
(function initNewsletterGrowth() {
  const SUBSCRIBED_KEY = 'ivt_newsletter_subscribed';
  const DISMISS_KEY = 'ivt_nl_popup_dismissed';
  const DISMISS_COOLDOWN_MS = 14 * 24 * 60 * 60 * 1000; // 14 jours
  const SCROLL_TRIGGER = 0.55; // 55 % de la page
  const TIME_TRIGGER_MS = 40 * 1000; // filet de sécurité

  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };
  const write = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* localStorage indisponible — pas bloquant */
    }
  };

  const isSubscribed = () => read(SUBSCRIBED_KEY) === '1';
  const markSubscribed = () => write(SUBSCRIBED_KEY, '1');

  // ── Soumission AJAX partagée ───────────────────────────────────────────
  const submitForm = (form) =>
    fetch(form.action, {
      method: 'POST',
      headers: { 'X-Requested-With': 'fetch', Accept: 'application/json' },
      body: new FormData(form),
    }).then((res) => res.json().then((data) => ({ ok: res.ok, data })));

  // ── Amélioration du formulaire de pied de page ─────────────────────────
  (function enhanceFooterForm() {
    const form = document.querySelector('.newsletter__form');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      const consent = form.querySelector('input[name="consent_rgpd"]');
      const email = form.querySelector('input[name="email"]');
      if (!form.checkValidity() || (consent && !consent.checked) || !email || !email.value) {
        return; // laisse la validation native / le POST classique opérer
      }
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      submitForm(form)
        .then(({ ok, data }) => {
          if (ok && data && data.subscribed) markSubscribed();
          const msg = (data && data.message) || '';
          if (msg) {
            const note = document.createElement('p');
            note.className = ok ? 'newsletter__inline-ok' : 'newsletter__inline-err';
            note.setAttribute('role', 'status');
            note.textContent = msg;
            form.replaceChildren(note);
          }
        })
        .catch(() => {
          if (btn) btn.disabled = false;
          form.submit(); // dégradation : POST classique
        });
    });
  })();

  // ── Pop-up ─────────────────────────────────────────────────────────────
  const popup = document.getElementById('nl-popup');
  if (!popup) return;

  const dismissedAt = Number(read(DISMISS_KEY) || 0);
  const onCooldown = dismissedAt && Date.now() - dismissedAt < DISMISS_COOLDOWN_MS;
  if (isSubscribed() || onCooldown) {
    popup.remove();
    return;
  }

  const dialog = popup.querySelector('.nl-popup__dialog');
  const backdrop = document.getElementById('nl-popup-backdrop');
  const closeBtn = document.getElementById('nl-popup-close');
  const dismissBtn = document.getElementById('nl-popup-dismiss');
  const form = document.getElementById('nl-popup-form');
  const emailInput = document.getElementById('nl-popup-email');
  const errorEl = document.getElementById('nl-popup-error');
  const bodyEl = document.getElementById('nl-popup-body');
  const thanksEl = document.getElementById('nl-popup-thanks');

  let opened = false;
  let closed = false;

  const open = () => {
    if (opened || closed) return;
    opened = true;
    teardownTriggers();
    popup.hidden = false;
    // force reflow pour la transition d'entrée
    void popup.offsetWidth;
    popup.classList.add('is-visible');
    document.documentElement.classList.add('nl-popup-lock');
    if (emailInput) {
      try {
        emailInput.focus({ preventScroll: true });
      } catch {
        emailInput.focus();
      }
    }
    document.addEventListener('keydown', onKeydown);
  };

  const remove = () => {
    popup.classList.remove('is-visible');
    document.documentElement.classList.remove('nl-popup-lock');
    document.removeEventListener('keydown', onKeydown);
    setTimeout(() => popup.remove(), 280);
  };

  const dismiss = () => {
    if (closed) return;
    closed = true;
    write(DISMISS_KEY, String(Date.now()));
    remove();
  };

  const onKeydown = (e) => {
    if (e.key === 'Escape') dismiss();
  };

  if (closeBtn) closeBtn.addEventListener('click', dismiss);
  if (dismissBtn) dismissBtn.addEventListener('click', dismiss);
  if (backdrop) backdrop.addEventListener('click', dismiss);
  if (dialog) dialog.addEventListener('click', (e) => e.stopPropagation());

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      if (errorEl) errorEl.hidden = true;
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      submitForm(form)
        .then(({ ok, data }) => {
          if (ok && data && data.subscribed) {
            markSubscribed();
            closed = true;
            if (bodyEl) bodyEl.hidden = true;
            if (thanksEl) thanksEl.hidden = false;
            setTimeout(remove, 2600);
          } else {
            if (btn) btn.disabled = false;
            if (errorEl) {
              if (data && data.message) errorEl.textContent = data.message;
              errorEl.hidden = false;
            }
          }
        })
        .catch(() => {
          if (btn) btn.disabled = false;
          if (errorEl) errorEl.hidden = false;
        });
    });
  }

  // ── Déclencheurs ───────────────────────────────────────────────────────
  const onExitIntent = (e) => {
    if (e.clientY <= 0) open();
  };
  const onScroll = () => {
    const doc = document.documentElement;
    const scrollable = doc.scrollHeight - doc.clientHeight;
    if (scrollable > 0 && (doc.scrollTop || window.pageYOffset) / scrollable >= SCROLL_TRIGGER) {
      open();
    }
  };
  let timer = null;

  function teardownTriggers() {
    document.removeEventListener('mouseout', onExitIntent);
    window.removeEventListener('scroll', onScroll);
    if (timer) clearTimeout(timer);
  }

  // Exit-intent réservé aux écrans pointeur fin (desktop) ; sur mobile c'est le
  // scroll + le délai qui prennent le relais.
  const finePointer = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
  if (finePointer) document.addEventListener('mouseout', onExitIntent);
  window.addEventListener('scroll', onScroll, { passive: true });
  timer = setTimeout(open, TIME_TRIGGER_MS);
})();
