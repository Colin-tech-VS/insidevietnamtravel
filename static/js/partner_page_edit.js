document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('partner-page-wizard');
  const form = document.getElementById('partner-page-form');
  if (!root || !form) return;

  const data = window.PARTNER_PAGE_DATA || {};
  const pitchMin = Number(root.dataset.pitchMin) || 30;
  const offerMin = Number(root.dataset.offerMin) || 40;
  const aiReview = root.dataset.aiReview === '1';

  const steps = Array.from(root.querySelectorAll('.partner-page-step'));
  const progressSteps = Array.from(root.querySelectorAll('.partner-page-progress .prepare-progress__step'));
  const btnPrev = document.getElementById('page-prev');
  const btnNext = document.getElementById('page-next');
  const btnSubmit = document.getElementById('page-submit');
  const errEl = document.getElementById('page-wizard-error');
  const stepCurrentEl = document.getElementById('page-step-current');
  const readinessFill = document.getElementById('page-readiness-fill');
  const readinessPct = document.getElementById('page-readiness-pct');
  const readinessBar = root.querySelector('.partner-page-readiness__bar');

  const pitchField = document.getElementById('pitch');
  const offerField = document.getElementById('offer_details');
  const highlightsInput = document.getElementById('highlights');
  const highlightsExtra = document.getElementById('highlights-extra');
  const cityInput = document.getElementById('city');
  const cityOtherWrap = document.getElementById('city-other-wrap');
  const cityOther = document.getElementById('city-other');
  const contactNote = document.getElementById('contact_note');
  const contactDetailWrap = document.getElementById('contact-detail-wrap');
  const contactDetail = document.getElementById('contact-detail');
  const contactDetailLabel = document.getElementById('contact-detail-label');
  const contactRadios = Array.from(form.querySelectorAll('input[name="contact_type"]'));

  const chipButtons = Array.from(document.querySelectorAll('#highlight-chips .partner-chip'));
  const cityButtons = Array.from(document.querySelectorAll('#city-chips .partner-chip'));
  const contactOptions = Array.from(document.querySelectorAll('.partner-contact-card'));

  let current = 1;
  const total = steps.length;
  const selectedChips = new Set();

  function showError(text) {
    if (!errEl) return;
    errEl.hidden = !text;
    errEl.textContent = text || '';
  }

  function syncContactCards() {
    contactOptions.forEach((card) => {
      const input = card.querySelector('input[type="radio"]');
      card.classList.toggle('is-selected', Boolean(input?.checked));
    });
  }

  function parseSavedHighlights() {
    const raw = (data.savedHighlights || highlightsInput?.value || '').trim();
    if (!raw) return;
    const parts = raw.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);
    parts.forEach((part) => {
      const match = chipButtons.find((b) => b.dataset.chip === part);
      if (match) {
        selectedChips.add(part);
        match.classList.add('is-selected');
        match.setAttribute('aria-pressed', 'true');
      } else if (highlightsExtra) {
        highlightsExtra.value = part;
      }
    });
    syncHighlightsField();
  }

  function syncHighlightsField() {
    const extra = (highlightsExtra?.value || '').trim();
    const items = [...selectedChips];
    if (extra) items.push(extra);
    if (highlightsInput) highlightsInput.value = items.join('\n');
    const countEl = document.getElementById('highlights-count');
    if (countEl) countEl.textContent = String(items.length);
  }

  chipButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const chip = btn.dataset.chip;
      if (selectedChips.has(chip)) {
        selectedChips.delete(chip);
        btn.classList.remove('is-selected');
        btn.setAttribute('aria-pressed', 'false');
      } else {
        selectedChips.add(chip);
        btn.classList.add('is-selected');
        btn.setAttribute('aria-pressed', 'true');
      }
      syncHighlightsField();
      updateReadiness();
    });
  });

  highlightsExtra?.addEventListener('input', () => {
    syncHighlightsField();
    updateReadiness();
  });

  function syncCitySelection(selectedBtn) {
    cityButtons.forEach((btn) => {
      const on = btn === selectedBtn;
      btn.classList.toggle('is-selected', on);
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    const city = selectedBtn?.dataset.city || '';
    if (city === 'Autre') {
      cityOtherWrap.hidden = false;
      cityInput.value = (cityOther?.value || '').trim();
    } else {
      cityOtherWrap.hidden = true;
      cityInput.value = city;
    }
    updateReadiness();
  }

  cityButtons.forEach((btn) => {
    btn.addEventListener('click', () => syncCitySelection(btn));
  });

  cityOther?.addEventListener('input', () => {
    if (cityInput) cityInput.value = (cityOther.value || '').trim();
    updateReadiness();
  });

  function initCity() {
    const val = (cityInput?.value || '').trim();
    const preset = cityButtons.find((b) => b.dataset.city === val);
    if (preset) {
      syncCitySelection(preset);
      return;
    }
    if (val) {
      const autre = cityButtons.find((b) => b.dataset.city === 'Autre');
      if (autre) {
        syncCitySelection(autre);
        if (cityOther) cityOther.value = val;
      }
    }
  }

  function contactTypeFromSaved(note) {
    const n = (note || '').toLowerCase();
    if (n.includes('whatsapp')) return 'whatsapp';
    if (n.includes('http') || n.includes('www.')) return 'website';
    if (n.includes('tel') || n.includes('phone') || n.includes('téléphone')) return 'phone';
    return 'email';
  }

  function updateContactNote() {
    const type = contactRadios.find((r) => r.checked)?.value || 'email';
    if (type === 'email') {
      contactDetailWrap.hidden = true;
      contactNote.value = data.email || '';
      return;
    }
    contactDetailWrap.hidden = false;
    if (type === 'whatsapp') {
      contactDetailLabel.textContent = 'Numéro WhatsApp';
      contactDetail.placeholder = '+84 …';
      const val = contactDetail.value.trim();
      contactNote.value = val ? `WhatsApp : ${val}` : '';
    } else if (type === 'website') {
      contactDetailLabel.textContent = 'URL de votre site';
      contactDetail.placeholder = 'https://…';
      const val = contactDetail.value.trim() || data.website || '';
      contactNote.value = val;
    } else {
      contactDetailLabel.textContent = 'Numéro de téléphone';
      contactDetail.placeholder = '+84 …';
      const val = contactDetail.value.trim();
      contactNote.value = val ? `Téléphone : ${val}` : '';
    }
  }

  function initContact() {
    const saved = (data.savedContact || contactNote?.value || '').trim();
    const type = contactTypeFromSaved(saved);
    const radio = contactRadios.find((r) => r.value === type);
    if (radio) radio.checked = true;
    syncContactCards();

    if (type === 'whatsapp') {
      contactDetail.value = saved.replace(/^whatsapp\s*:\s*/i, '');
    } else if (type === 'website') {
      contactDetail.value = saved || data.website || '';
    } else if (type === 'phone') {
      contactDetail.value = saved.replace(/^téléphone\s*:\s*/i, '').replace(/^telephone\s*:\s*/i, '');
    }
    updateContactNote();
  }

  contactRadios.forEach((r) => {
    r.addEventListener('change', () => {
      syncContactCards();
      updateContactNote();
      updateReadiness();
    });
  });
  contactDetail?.addEventListener('input', () => {
    updateContactNote();
    updateReadiness();
  });

  contactOptions.forEach((card) => {
    card.addEventListener('click', () => {
      const radio = card.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        syncContactCards();
        updateContactNote();
        updateReadiness();
      }
    });
  });

  function updateCharField(field, countEl, barEl, wrapEl, min, max) {
    if (!field) return 0;
    const len = field.value.length;
    if (countEl) countEl.textContent = String(len);
    const ratio = Math.min(len / max, 1);
    if (barEl) barEl.style.width = `${ratio * 100}%`;
    const ok = len >= min;
    wrapEl?.classList.toggle('is-valid', ok);
    wrapEl?.classList.toggle('is-warn', len > 0 && !ok);
    barEl?.classList.toggle('is-valid', ok);
    return ok ? 1 : len > 0 ? 0.5 : 0;
  }

  function updateReadiness() {
    const pitchScore = updateCharField(
      pitchField,
      document.getElementById('pitch-count'),
      document.getElementById('pitch-bar'),
      document.getElementById('pitch-count-wrap'),
      pitchMin,
      500,
    );
    const offerScore = updateCharField(
      offerField,
      document.getElementById('offer-count'),
      document.getElementById('offer-bar'),
      document.getElementById('offer-count-wrap'),
      offerMin,
      5000,
    );
    const highlightScore = selectedChips.size || (highlightsExtra?.value || '').trim() ? 1 : 0.3;
    const cityScore = (cityInput?.value || '').trim() ? 1 : 0;
    const contactScore = (contactNote?.value || '').trim() ? 1 : 0;

    const pct = Math.round(
      pitchScore * 35 +
      highlightScore * 15 +
      offerScore * 35 +
      cityScore * 8 +
      contactScore * 7,
    );
    if (readinessFill) readinessFill.style.width = `${pct}%`;
    if (readinessPct) readinessPct.textContent = String(pct);
    if (readinessBar) readinessBar.setAttribute('aria-valuenow', String(pct));
  }

  function validateStep(step) {
    if (step === 1) {
      const len = (pitchField?.value || '').trim().length;
      if (len < pitchMin) {
        showError(`Accroche trop courte — ${pitchMin} caractères minimum.`);
        pitchField?.focus();
        return false;
      }
    }
    if (step === 3) {
      const offerLen = (offerField?.value || '').trim().length;
      if (offerLen < offerMin) {
        showError(`Décrivez votre offre — ${offerMin} caractères minimum.`);
        offerField?.focus();
        return false;
      }
      if (!(cityInput?.value || '').trim()) {
        showError('Sélectionnez une ville ou région.');
        return false;
      }
      if (!(contactNote?.value || '').trim()) {
        showError('Renseignez votre contact préféré.');
        return false;
      }
    }
    showError('');
    return true;
  }

  function go(step) {
    current = Math.max(1, Math.min(total, step));
    steps.forEach((el) => {
      const n = Number(el.dataset.step);
      el.hidden = n !== current;
      el.classList.toggle('is-active', n === current);
    });
    progressSteps.forEach((el) => {
      const n = Number(el.dataset.step);
      el.classList.toggle('is-active', n === current);
      el.classList.toggle('is-done', n < current);
    });
    if (btnPrev) btnPrev.hidden = current <= 1;
    if (btnNext) btnNext.hidden = current >= total;
    if (stepCurrentEl) stepCurrentEl.textContent = String(current);
    showError('');
    updateReadiness();
  }

  progressSteps.forEach((el) => {
    el.addEventListener('click', () => {
      const target = Number(el.dataset.step);
      if (target < current) {
        go(target);
        return;
      }
      for (let s = current; s < target; s += 1) {
        if (!validateStep(s)) {
          go(s);
          return;
        }
      }
      go(target);
    });
  });

  btnPrev?.addEventListener('click', () => go(current - 1));
  btnNext?.addEventListener('click', () => {
    if (!validateStep(current)) return;
    go(current + 1);
  });

  form.addEventListener('submit', (e) => {
    syncHighlightsField();
    updateContactNote();
    for (let s = 1; s <= total; s += 1) {
      if (!validateStep(s)) {
        e.preventDefault();
        go(s);
        return;
      }
    }
    if (aiReview && e.submitter?.value === 'submit_ai') {
      e.preventDefault();
      showError('Vérification déjà en cours.');
    }
  });

  pitchField?.addEventListener('input', updateReadiness);
  offerField?.addEventListener('input', updateReadiness);

  parseSavedHighlights();
  initCity();
  initContact();
  go(1);
});
