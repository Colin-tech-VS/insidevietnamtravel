document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('partner-wizard');
  if (!root) return;

  const isEn = root.dataset.lang === 'en';
  const msg = {
    chooseOption: isEn ? 'Please choose an option.' : 'Choisissez une option.',
    required: isEn ? 'Please complete all required fields.' : 'Complétez les champs obligatoires.',
    bioMin: isEn ? 'Partnership pitch must be at least 40 characters.' : 'La proposition de partenariat doit contenir au moins 40 caractères.',
    passMin: isEn ? 'Password must be at least 8 characters.' : 'Mot de passe : 8 caractères minimum.',
    passMatch: isEn ? 'Passwords do not match.' : 'Les mots de passe ne correspondent pas.',
    consent: isEn ? 'Please accept the privacy policy.' : 'Acceptez la politique de confidentialité.',
  };

  const steps = Array.from(root.querySelectorAll('.partner-step'));
  const progress = Array.from(root.querySelectorAll('.pp-stepper__item'));
  const btnPrev = document.getElementById('partner-prev');
  const btnNext = document.getElementById('partner-next');
  const btnSubmit = document.getElementById('partner-submit');
  const errEl = document.getElementById('partner-wizard-error');
  const stepCurrentEl = document.getElementById('partner-step-current');
  const progressFill = document.getElementById('partner-progress-fill');
  const typeCards = Array.from(root.querySelectorAll('.pp-type'));
  const bioField = root.querySelector('#pp-bio');
  const bioCount = document.getElementById('pp-bio-count');
  let current = 1;
  const total = steps.length;

  function showError(text) {
    if (!errEl) return;
    if (text) {
      errEl.textContent = text;
      errEl.hidden = false;
    } else {
      errEl.hidden = true;
      errEl.textContent = '';
    }
  }

  function syncTypeCards() {
    typeCards.forEach((card) => {
      const input = card.querySelector('input[type="radio"]');
      card.classList.toggle('is-selected', Boolean(input?.checked));
    });
  }

  typeCards.forEach((card) => {
    const input = card.querySelector('input[type="radio"]');
    input?.addEventListener('change', syncTypeCards);
    card.addEventListener('click', () => {
      const input = card.querySelector('input[type="radio"]');
      if (input) input.checked = true;
      syncTypeCards();
    });
  });

  function updateBioCount() {
    if (!bioField || !bioCount) return;
    bioCount.textContent = String(bioField.value.length);
  }

  bioField?.addEventListener('input', updateBioCount);
  updateBioCount();

  function go(step) {
    current = Math.max(1, Math.min(total, step));
    steps.forEach((el) => {
      const n = Number(el.dataset.step);
      el.hidden = n !== current;
      el.classList.toggle('is-active', n === current);
    });
    progress.forEach((el) => {
      const n = Number(el.dataset.step);
      el.classList.toggle('is-active', n === current);
      el.classList.toggle('is-done', n < current);
    });
    if (btnPrev) btnPrev.hidden = current <= 1;
    if (btnNext) btnNext.hidden = current >= total;
    if (btnSubmit) btnSubmit.hidden = current < total;
    if (stepCurrentEl) stepCurrentEl.textContent = String(current);
    if (progressFill) {
      const pct = current === 1 ? 12.5 : ((current - 0.5) / total) * 100;
      progressFill.style.width = `${pct}%`;
    }
    showError('');
    const applySection = document.getElementById('partner-apply-form');
    applySection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function validateStep(step) {
    const panel = steps.find((el) => Number(el.dataset.step) === step);
    if (!panel) return true;
    const required = panel.querySelectorAll('[required]');
    for (const field of required) {
      if (field.type === 'radio') {
        const name = field.name;
        if (!panel.querySelector(`input[name="${name}"]:checked`)) {
          showError(msg.chooseOption);
          return false;
        }
      } else if (!field.value.trim()) {
        field.focus();
        showError(msg.required);
        return false;
      }
    }
    if (step === 2) {
      const bio = root.querySelector('#pp-bio')?.value?.trim() || '';
      if (bio.length > 0 && bio.length < 40) {
        showError(msg.bioMin);
        root.querySelector('#pp-bio')?.focus();
        return false;
      }
    }
    if (step === 4) {
      const p1 = root.querySelector('#pp-pass')?.value || '';
      const p2 = root.querySelector('#pp-pass2')?.value || '';
      if (p1.length < 8) {
        showError(msg.passMin);
        return false;
      }
      if (p1 !== p2) {
        showError(msg.passMatch);
        return false;
      }
      if (!root.querySelector('[name="consent_rgpd"]')?.checked) {
        showError(msg.consent);
        return false;
      }
    }
    return true;
  }

  btnPrev?.addEventListener('click', () => go(current - 1));
  btnNext?.addEventListener('click', () => {
    if (validateStep(current)) go(current + 1);
  });

  btnSubmit?.addEventListener('click', async () => {
    if (!validateStep(current)) return;
    const registerUrl = root.dataset.registerUrl;
    const dashboardUrl = root.dataset.dashboardUrl;
    const payload = {
      profile_type: root.querySelector('input[name="profile_type"]:checked')?.value,
      business_name: root.querySelector('#pp-business')?.value?.trim(),
      city: root.querySelector('#pp-city')?.value?.trim(),
      bio: root.querySelector('#pp-bio')?.value?.trim(),
      services: root.querySelector('#pp-services')?.value?.trim(),
      social_links: root.querySelector('#pp-social')?.value?.trim(),
      phone: root.querySelector('#pp-phone')?.value?.trim(),
      languages: root.querySelector('#pp-langs')?.value?.trim(),
      first_name: root.querySelector('#pp-first')?.value?.trim(),
      last_name: root.querySelector('#pp-last')?.value?.trim(),
      email: root.querySelector('#pp-email')?.value?.trim(),
      password: root.querySelector('#pp-pass')?.value,
      password_confirm: root.querySelector('#pp-pass2')?.value,
      consent_rgpd: root.querySelector('[name="consent_rgpd"]')?.checked ? '1' : '',
      website: root.querySelector('[name="website"]')?.value || '',
    };
    btnSubmit.disabled = true;
    showError('');
    try {
      const res = await fetch(registerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || (isEn ? 'Registration failed' : 'Inscription impossible'));
      window.location.href = data.redirect || dashboardUrl;
    } catch (e) {
      showError(e.message);
      btnSubmit.disabled = false;
    }
  });

  syncTypeCards();
  go(1);
});
