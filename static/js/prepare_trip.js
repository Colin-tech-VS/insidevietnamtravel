(function () {
  const catalog = window.prepareTripCatalog;
  if (!catalog) return;

  const wizard = document.getElementById('prepare-wizard');
  const emailGate = document.getElementById('prepare-email-gate');
  const resultsEl = document.getElementById('prepare-results');
  if (!wizard || !emailGate || !resultsEl) return;

  const UNLOCK_KEY = 'ivt_prepare_unlocked';
  const TOTAL_STEPS = 5;
  const MIN_TRAVELERS = 1;
  const MAX_TRAVELERS = 20;
  const LANG = (document.documentElement.lang || 'fr').slice(0, 2);
  const state = { group: null, persons: null, style: null, duration: null, cities: [], step: 1 };
  const labels = catalog.labels || {};
  const cityList = catalog.cities || [];
  const cityRegion = {};
  cityList.forEach((c) => { cityRegion[c.id] = c.region; });

  const ICONS = {
    group: { solo: '🧳', couple: '💑', family: '👨‍👩‍👧', friends: '👯' },
    style: {
      culture: '🏛️',
      food: '🍜',
      adventure: '⛰️',
      romantic: '💕',
      roadtrip: '🚂',
      relax: '🏖️',
      budget: '🎒',
    },
    duration: { short: '7', medium: '10', long: '14+' },
  };

  function isUnlocked() {
    try {
      return sessionStorage.getItem(UNLOCK_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function setUnlocked() {
    try {
      sessionStorage.setItem(UNLOCK_KEY, '1');
    } catch (e) { /* ignore */ }
  }

  function showEmailGate() {
    wizard.hidden = true;
    resultsEl.hidden = true;
    emailGate.hidden = false;
    emailGate.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const input = emailGate.querySelector('#prepare-email');
    if (input) input.focus();
  }

  function hideEmailGate() {
    emailGate.hidden = true;
  }

  function showEmailError(msg) {
    const err = document.getElementById('prepare-email-error');
    if (!err) return;
    err.textContent = msg || '';
    err.hidden = !msg;
  }

  function submitEmailGate(form) {
    const email = (form.email.value || '').trim();
    const consent = form.consent_rgpd.checked;
    if (!consent) {
      showEmailError(labels.gate_error_consent || '');
      return;
    }
    if (!email || !email.includes('@')) {
      showEmailError(labels.gate_error_email || '');
      return;
    }

    const btn = form.querySelector('.prepare-email-gate__submit');
    const btnLabel = btn ? btn.textContent : '';
    if (btn) {
      btn.disabled = true;
      btn.setAttribute('aria-busy', 'true');
      btn.textContent = labels.gate_loading || btnLabel;
    }
    showEmailError('');

    setUnlocked();
    showResultsShell();
    requestAnimationFrame(() => renderResultsContent());

    if (btn) {
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
      btn.textContent = btnLabel;
    }

    const val = (name) => (form[name] && form[name].value ? form[name].value.trim() : '');

    fetch(catalog.unlock_url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        email,
        consent_rgpd: '1',
        first_name: val('first_name'),
        phone: val('phone'),
        travel_period: val('travel_period'),
        budget: val('budget'),
        group: state.group || '',
        persons: state.persons || '',
        style: state.style || '',
        duration: state.duration || '',
        cities: state.cities || [],
      }),
      keepalive: true,
    }).catch(() => { /* résultats déjà affichés ; inscription retentée au prochain passage */ });
  }

  function requestResults() {
    if (isUnlocked()) renderResults();
    else showEmailGate();
  }

  function uniq(arr) {
    return [...new Set(arr)];
  }

  function fieldForStep(n) {
    if (n === 1) return 'group';
    if (n === 2) return 'persons';
    if (n === 3) return 'style';
    if (n === 4) return 'duration';
    return 'cities';
  }

  function defaultPersonsForGroup(groupId) {
    const item = (catalog.groups || []).find((g) => g.id === groupId);
    const sizes = (catalog.budget && catalog.budget.group_size) || {};
    return (item && item.default_persons) || sizes[groupId] || 2;
  }

  function labelForGroup(id) {
    const item = (catalog.groups || []).find((g) => g.id === id);
    return item ? item.label : id;
  }

  function labelForStyle(id) {
    const item = (catalog.styles || []).find((s) => s.id === id);
    return item ? item.label : id;
  }

  function labelForDuration(id) {
    const item = (catalog.durations || []).find((d) => d.id === id);
    return item ? item.label : id;
  }

  function fmtEur(n) {
    const locale = LANG === 'en' ? 'en-GB' : 'fr-FR';
    return Math.round(n).toLocaleString(locale) + ' €';
  }

  function resolveSlugs() {
    const profile = catalog.profiles[state.style] || catalog.profiles.culture;
    const boost = catalog.group_boost[state.group] || {};
    let itinSlugs = uniq([
      ...(catalog.duration_itineraries[state.duration] || []),
      ...(profile.itinerary_slugs || []),
    ]);
    if (boost.duration) {
      itinSlugs = uniq(itinSlugs.concat(catalog.duration_itineraries[boost.duration] || []));
    }
    // Les villes choisies par l'utilisateur priment sur les destinations du profil.
    const destSlugs = state.cities.length ? state.cities.slice() : (profile.destination_slugs || []);
    return {
      itinSlugs,
      destSlugs,
      artSlugs: profile.article_slugs || [],
      catKeys: profile.categories || [],
    };
  }

  function iconFor(field, id) {
    const set = ICONS[field] || {};
    return set[id] || '✦';
  }

  function updateNextButton() {
    const field = fieldForStep(state.step);
    const next = wizard.querySelector('.prepare-next');
    if (!next) return;
    let ready = false;
    if (field === 'cities') ready = state.cities.length > 0;
    else if (field === 'persons') ready = Number(state.persons) >= MIN_TRAVELERS;
    else ready = Boolean(state[field]);
    next.disabled = !ready;
    next.classList.toggle('is-disabled', !ready);
    next.setAttribute('aria-disabled', ready ? 'false' : 'true');
  }

  function renderOptions(container, items, field) {
    container.innerHTML = items.map((item) => {
      const icon = iconFor(field, item.id);
      const iconHtml = field === 'duration'
        ? `<span class="prepare-option__icon prepare-option__icon--days" aria-hidden="true"><span>${icon}</span><small>${(labels.days || 'days')}</small></span>`
        : `<span class="prepare-option__icon" aria-hidden="true">${icon}</span>`;
      return `<button type="button" class="prepare-option${state[field] === item.id ? ' is-selected' : ''}" data-value="${item.id}" data-field="${field}">
        ${iconHtml}
        <span class="prepare-option__body">
          <span class="prepare-option__label">${item.label}</span>
          ${item.desc ? `<span class="prepare-option__desc">${item.desc}</span>` : ''}
        </span>
        <span class="prepare-option__check" aria-hidden="true">✓</span>
      </button>`;
    }).join('');

    container.querySelectorAll('.prepare-option').forEach((btn) => {
      btn.addEventListener('click', () => {
        state[field] = btn.dataset.value;
        if (field === 'group') {
          state.persons = defaultPersonsForGroup(state.group);
          renderTravelersStep(wizard.querySelector('[data-step="2"] .prepare-travelers'));
        }
        container.querySelectorAll('.prepare-option').forEach((b) => b.classList.remove('is-selected'));
        btn.classList.add('is-selected');
        updateNextButton();
      });
    });
  }

  function renderTravelersStep(container) {
    if (!container) return;
    const count = Number(state.persons) || defaultPersonsForGroup(state.group) || 2;
    state.persons = count;
    container.innerHTML = `
      <div class="prepare-travelers__control">
        <button type="button" class="prepare-travelers__btn" data-action="dec" aria-label="${labels.travelers_decrease || '-'}">−</button>
        <div class="prepare-travelers__value">
          <span class="prepare-travelers__num" aria-live="polite">${count}</span>
          <span class="prepare-travelers__unit">${labels.budget_persons || ''}</span>
        </div>
        <button type="button" class="prepare-travelers__btn" data-action="inc" aria-label="${labels.travelers_increase || '+'}">+</button>
      </div>`;

    container.querySelector('[data-action="dec"]').addEventListener('click', () => {
      state.persons = Math.max(MIN_TRAVELERS, Number(state.persons) - 1);
      renderTravelersStep(container);
      updateNextButton();
    });
    container.querySelector('[data-action="inc"]').addEventListener('click', () => {
      state.persons = Math.min(MAX_TRAVELERS, Number(state.persons) + 1);
      renderTravelersStep(container);
      updateNextButton();
    });
    updateNextButton();
  }

  function cityOptionHtml(c) {
    const selected = state.cities.includes(c.id);
    const desc = c.tagline || c.region_label || '';
    return `<button type="button" class="prepare-option prepare-option--multi${selected ? ' is-selected' : ''}" data-value="${c.id}" aria-pressed="${selected}">
      <span class="prepare-option__icon" aria-hidden="true">📍</span>
      <span class="prepare-option__body">
        <span class="prepare-option__label">${c.name}</span>
        ${desc ? `<span class="prepare-option__desc">${desc}</span>` : ''}
      </span>
      <span class="prepare-option__check" aria-hidden="true">✓</span>
    </button>`;
  }

  function bindCityButtons(container) {
    container.querySelectorAll('.prepare-option').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.value;
        const idx = state.cities.indexOf(id);
        if (idx === -1) state.cities.push(id);
        else state.cities.splice(idx, 1);
        const on = state.cities.includes(id);
        btn.classList.toggle('is-selected', on);
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        updateNextButton();
      });
    });
  }

  function renderCityOptions(container) {
    const regions = catalog.city_regions || [];
    if (regions.length) {
      container.innerHTML = regions.map((region) => {
        const cards = (region.destinations || []).map((dest) => {
          const c = cityList.find((x) => x.id === dest.slug) || {
            id: dest.slug,
            name: dest.name,
            tagline: dest.tagline,
            region_label: region.label,
          };
          return cityOptionHtml(c);
        }).join('');
        return `<section class="prepare-region"><h3 class="prepare-region__title">${region.label}</h3><div class="prepare-options prepare-options--grid prepare-options--multi">${cards}</div></section>`;
      }).join('');
    } else {
      container.innerHTML = `<div class="prepare-options prepare-options--grid prepare-options--multi">${cityList.map(cityOptionHtml).join('')}</div>`;
    }
    bindCityButtons(container);
  }

  function showStep(n) {
    state.step = n;
    wizard.querySelectorAll('.prepare-step').forEach((el) => {
      const active = Number(el.dataset.step) === n;
      el.classList.toggle('is-active', active);
      el.hidden = !active;
    });
    wizard.querySelectorAll('.prepare-progress__step').forEach((step) => {
      const num = Number(step.dataset.step);
      step.classList.toggle('is-active', num === n);
      step.classList.toggle('is-done', num < n);
      step.classList.toggle('is-clickable', num < n);
      step.setAttribute('aria-current', num === n ? 'step' : 'false');
    });
    const back = wizard.querySelector('.prepare-back');
    const next = wizard.querySelector('.prepare-next');
    if (back) back.hidden = n === 1;
    if (next) {
      next.textContent = n === TOTAL_STEPS
        ? (labels.view_results || labels.results_title || 'Results')
        : (labels.next || 'Continue');
    }
    if (n === 2) {
      const travelersEl = wizard.querySelector('[data-step="2"] .prepare-travelers');
      if (travelersEl) renderTravelersStep(travelersEl);
    }
    updateNextButton();
  }

  function cardHtml(item, type) {
    const arrow = '<span class="prepare-card__arrow" aria-hidden="true">→</span>';
    if (type === 'itin') {
      return `<a href="${item.url}" class="prepare-card prepare-card--itin">
        <span class="prepare-card__meta">${item.duration} ${(catalog.labels && catalog.labels.days) || 'days'}</span>
        <h3>${item.title}</h3>
        <p>${item.summary}</p>
        <span class="prepare-card__hint">${item.budget_hint || ''}</span>
        ${arrow}
      </a>`;
    }
    if (type === 'dest') {
      return `<a href="${item.url}" class="prepare-card prepare-card--dest">
        <span class="prepare-card__meta">${labels.dest_section || 'Destination'}</span>
        <h3>${item.name}</h3>
        <p>${item.tagline}</p>
        ${arrow}
      </a>`;
    }
    if (type === 'art') {
      return `<a href="${item.url}" class="prepare-card prepare-card--art">
        <span class="prepare-card__meta">${item.category_label}</span>
        <h3>${item.title}</h3>
        <p>${item.excerpt}</p>
        ${arrow}
      </a>`;
    }
    return `<a href="${item.url}" class="prepare-card prepare-card--cat">
      <span class="prepare-card__meta">${labels.cat_section || 'Blog'}</span>
      <h3>${item.label}</h3>
      <p>${item.description}</p>
      ${arrow}
    </a>`;
  }

  function block(icon, title, inner) {
    return `<section class="prepare-results__block"><h3><span class="prepare-results__icon" aria-hidden="true">${icon}</span>${title}</h3>${inner}</section>`;
  }

  function computeBudget() {
    const b = catalog.budget || {};
    const tierKey = (b.style_tier || {})[state.style] || 'comfort';
    const tier = (b.tiers || {})[tierKey] || { perday: {}, perday_total: 0 };
    const perday = tier.perday || {};
    const days = (b.duration_days || {})[state.duration] || 10;
    const persons = Number(state.persons) || (b.group_size || {})[state.group] || 2;
    const legs = Math.max(0, state.cities.length - 1);
    const intercity = legs * (b.intercity_per_leg || 0);

    // Coûts sur place par personne (montant journalier × jours), par catégorie.
    const daily = {};
    let dailyTotal = 0;
    Object.keys(perday).forEach((k) => {
      daily[k] = perday[k] * days;
      dailyTotal += daily[k];
    });
    if (daily.transport != null) daily.transport += intercity;
    dailyTotal += intercity;

    const oneoff = b.oneoff || [];
    const oneoffTotal = oneoff.reduce((s, o) => s + (o.amount || 0), 0);
    const perPerson = dailyTotal + oneoffTotal;
    return {
      days, persons, legs, intercity, daily, dailyTotal, oneoff, oneoffTotal,
      perPerson, group: perPerson * persons,
    };
  }

  function budgetHtml() {
    const r = computeBudget();
    const cats = catalog.budget.categories || [];
    const rows = cats.map((c) => {
      const amount = r.daily[c.key] || 0;
      const extra = c.key === 'transport' && r.intercity > 0
        ? ` <small class="prepare-budget__extra">(+${fmtEur(r.intercity)} ${labels.budget_intercity || ''})</small>`
        : '';
      return `<li><span>${c.icon || ''} ${c.label}${extra}</span><strong>${fmtEur(amount)}</strong></li>`;
    }).join('');
    const oneoffRows = r.oneoff.map((o) => (
      `<li><span>${o.label}${o.hint ? ` <small>${o.hint}</small>` : ''}</span><strong>${fmtEur(o.amount)}</strong></li>`
    )).join('');
    const meta = `${r.days} ${labels.days || 'days'} · ${state.cities.length} 📍 · ${r.persons} ${labels.budget_persons || ''}`;
    const inner = `
      <div class="prepare-budget">
        <p class="prepare-budget__meta">${meta}</p>
        <div class="prepare-budget__cols">
          <div class="prepare-budget__col">
            <h4>${labels.budget_daily || ''} <small>· ${labels.budget_perperson || ''}</small></h4>
            <ul class="prepare-budget__list">${rows}</ul>
          </div>
          <div class="prepare-budget__col">
            <h4>${labels.budget_oneoff || ''} <small>· ${labels.budget_perperson || ''}</small></h4>
            <ul class="prepare-budget__list">${oneoffRows}</ul>
          </div>
        </div>
        <div class="prepare-budget__totals">
          <div class="prepare-budget__total prepare-budget__total--pp">
            <span>${labels.budget_total || ''} · ${labels.budget_perperson || ''}</span>
            <strong>${fmtEur(r.perPerson)}</strong>
          </div>
          <div class="prepare-budget__total prepare-budget__total--group">
            <span>${labels.budget_total || ''} · ${labels.budget_group || ''} (${r.persons} ${labels.budget_persons || ''})</span>
            <strong>${fmtEur(r.group)}</strong>
          </div>
        </div>
        <p class="prepare-budget__note">${labels.budget_note || ''}</p>
      </div>`;
    return block('💶', labels.budget_section || 'Budget', inner);
  }

  function computeTips() {
    const t = catalog.tips || {};
    let list = [...(t.general || [])];
    list = list.concat((t.by_style || {})[state.style] || []);
    list = list.concat((t.by_group || {})[state.group] || []);
    const regions = uniq(state.cities.map((s) => cityRegion[s]).filter(Boolean));
    regions.forEach((reg) => { list = list.concat((t.by_region || {})[reg] || []); });
    return uniq(list).slice(0, 8);
  }

  function tipsHtml() {
    const tips = computeTips();
    if (!tips.length) return '';
    const items = tips.map((tip) => `<li>${tip}</li>`).join('');
    return block('💡', labels.tips_section || 'Tips', `<ul class="prepare-tips">${items}</ul>`);
  }

  function affLink(url, text) {
    return `<a href="${url}" class="prepare-reco__link" target="_blank" rel="sponsored noopener" data-no-loader>${text} <span aria-hidden="true">↗</span></a>`;
  }

  function recosHtml() {
    const dests = catalog.destinations || {};
    const recos = catalog.recos || {};
    const selected = state.cities.map((s) => dests[s]).filter(Boolean);

    const cards = [];

    if (selected.length) {
      const hotelLinks = selected
        .filter((d) => d.hotel_url)
        .map((d) => affLink(d.hotel_url, d.name)).join('');
      cards.push(`<article class="prepare-reco">
        <span class="prepare-reco__icon" aria-hidden="true">🏨</span>
        <h4>${labels.reco_hotels || ''}</h4>
        <p>${labels.reco_hotels_desc || ''}</p>
        <div class="prepare-reco__links">${hotelLinks}</div>
      </article>`);

      const actLinks = selected
        .filter((d) => d.activity_url)
        .map((d) => affLink(d.activity_url, d.name)).join('');
      cards.push(`<article class="prepare-reco">
        <span class="prepare-reco__icon" aria-hidden="true">🎟️</span>
        <h4>${labels.reco_activities || ''}</h4>
        <p>${labels.reco_activities_desc || ''}</p>
        <div class="prepare-reco__links">${actLinks}</div>
      </article>`);
    }

    const esimLinks = [
      recos.esim_airalo_url ? affLink(recos.esim_airalo_url, 'Airalo') : '',
      recos.esim_holafly_url ? affLink(recos.esim_holafly_url, 'Holafly') : '',
    ].join('');
    cards.push(`<article class="prepare-reco">
      <span class="prepare-reco__icon" aria-hidden="true">📶</span>
      <h4>${labels.reco_esim || ''}</h4>
      <p>${labels.reco_esim_desc || ''}</p>
      <div class="prepare-reco__links">${esimLinks}</div>
    </article>`);

    if (recos.insurance_url) {
      cards.push(`<article class="prepare-reco">
        <span class="prepare-reco__icon" aria-hidden="true">🛡️</span>
        <h4>${labels.reco_insurance || ''}</h4>
        <p>${labels.reco_insurance_desc || ''}</p>
        <div class="prepare-reco__links">${affLink(recos.insurance_url, labels.reco_view || 'View')}</div>
      </article>`);
    }

    const inner = `<div class="prepare-recos">${cards.join('')}</div>
      <p class="prepare-recos__disclosure">${labels.reco_disclosure || ''}</p>`;
    return block('✨', labels.recos_section || 'Recommendations', inner);
  }

  function summaryHtml() {
    const cityNames = state.cities.map((id) => {
      const c = cityList.find((x) => x.id === id);
      return c ? c.name : id;
    });
    const items = [
      { icon: '👥', label: labelForGroup(state.group), value: `${state.persons} ${labels.budget_persons || ''}` },
      { icon: '✈️', label: labels.step3 || '', value: labelForStyle(state.style) },
      { icon: '📅', label: labels.step4 || '', value: labelForDuration(state.duration) },
      { icon: '📍', label: labels.step5 || '', value: cityNames.length ? cityNames.join(', ') : '—' },
    ];
    const cards = items.map((item) => (
      `<div class="prepare-summary__item"><span class="prepare-summary__icon" aria-hidden="true">${item.icon}</span><div><span class="prepare-summary__label">${item.label}</span><strong class="prepare-summary__value">${item.value}</strong></div></div>`
    )).join('');
    return block('📋', labels.summary_section || 'Profile', `<div class="prepare-summary">${cards}</div>`);
  }

  function showResultsShell() {
    hideEmailGate();
    wizard.hidden = true;
    resultsEl.hidden = false;
    resultsEl.querySelector('.prepare-results__title').textContent = labels.results_title || '';
    resultsEl.querySelector('.prepare-results__sub').textContent = labels.results_sub || '';
    const backBtn = resultsEl.querySelector('.prepare-results-back');
    if (backBtn) backBtn.textContent = labels.results_back || labels.back || '';
    resultsEl.querySelector('.prepare-restart').textContent = labels.restart || '';
    resultsEl.querySelector('.prepare-results__sections').innerHTML =
      `<p class="prepare-results__loading" aria-live="polite">${labels.gate_loading || '…'}</p>`;
    resultsEl.scrollIntoView({ behavior: 'auto', block: 'start' });
  }

  function renderResultsContent() {
    const { itinSlugs, destSlugs, artSlugs, catKeys } = resolveSlugs();
    const articles = catalog.articles || {};
    const extraArts = Object.values(articles).filter(
      (a) => catKeys.includes(a.category) && !artSlugs.includes(a.slug),
    ).slice(0, 4);

    const sections = [];

    sections.push(summaryHtml());

    // 1. Budget estimé (réponse directe à "estimation plus précise").
    if (catalog.budget && state.style) sections.push(budgetHtml());

    // 2. Itinéraires.
    const itins = itinSlugs.map((s) => catalog.itineraries[s]).filter(Boolean);
    if (itins.length) {
      sections.push(block('🗺️', labels.itin_section, `<div class="prepare-cards">${itins.map((i) => cardHtml(i, 'itin')).join('')}</div>`));
    }

    // 3. Destinations (villes choisies).
    const dests = destSlugs.map((s) => catalog.destinations[s]).filter(Boolean);
    if (dests.length) {
      sections.push(block('📍', labels.dest_section, `<div class="prepare-cards">${dests.map((d) => cardHtml(d, 'dest')).join('')}</div>`));
    }

    // 4. Conseils.
    sections.push(tipsHtml());

    // 5. Guides à lire.
    const arts = artSlugs.map((s) => articles[s]).filter(Boolean).concat(extraArts);
    if (arts.length) {
      sections.push(block('📖', labels.art_section, `<div class="prepare-cards">${arts.map((a) => cardHtml(a, 'art')).join('')}</div>`));
    }

    // 6. Catégories du blog.
    const cats = catKeys.map((k) => catalog.categories[k]).filter(Boolean);
    if (cats.length) {
      sections.push(block('🏷️', labels.cat_section, `<div class="prepare-cards">${cats.map((c) => cardHtml(c, 'cat')).join('')}</div>`));
    }

    // 7. Recommandations affiliées (à la fin).
    sections.push(recosHtml());

    resultsEl.querySelector('.prepare-results__sections').innerHTML =
      sections.filter(Boolean).join('') || `<p class="prepare-results__empty">${labels.empty || ''}</p>`;

    if (window.ivtProfile && window.ivtProfile.saveTripPrefs) {
      window.ivtProfile.saveTripPrefs({
        group: state.group,
        persons: state.persons,
        style: state.style,
        duration: state.duration,
        cities: state.cities,
      });
    }
  }

  function renderResults() {
    showResultsShell();
    renderResultsContent();
  }

  function applySavedProfile() {
    if (!window.ivtProfile || !window.ivtProfile.enabled()) return;
    var p = window.ivtProfile.load();
    if (!p) return;
    if (p.g) state.group = p.g;
    if (p.n) state.persons = Number(p.n) || null;
    if (p.s) state.style = p.s;
    if (p.d) state.duration = p.d;
    if (p.c && p.c.length) state.cities = p.c.slice();
    if (state.group && !state.persons) state.persons = defaultPersonsForGroup(state.group);
  }

  function init() {
    applySavedProfile();
    const step1 = wizard.querySelector('[data-step="1"] .prepare-options');
    const step2 = wizard.querySelector('[data-step="2"] .prepare-travelers');
    const step3 = wizard.querySelector('[data-step="3"] .prepare-options');
    const step4 = wizard.querySelector('[data-step="4"] .prepare-options');
    const step5 = wizard.querySelector('[data-step="5"] .prepare-cities');
    renderOptions(step1, catalog.groups, 'group');
    renderTravelersStep(step2);
    renderOptions(step3, catalog.styles, 'style');
    renderOptions(step4, catalog.durations, 'duration');
    if (step5) renderCityOptions(step5);

    wizard.querySelectorAll('.prepare-progress__step').forEach((stepEl) => {
      const goBack = () => {
        const num = Number(stepEl.dataset.step);
        if (num < state.step) showStep(num);
      };
      stepEl.addEventListener('click', goBack);
      stepEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          goBack();
        }
      });
    });

    wizard.querySelector('.prepare-back').addEventListener('click', () => showStep(state.step - 1));
    wizard.querySelector('.prepare-next').addEventListener('click', () => {
      const field = fieldForStep(state.step);
      let ready = false;
      if (field === 'cities') ready = state.cities.length > 0;
      else if (field === 'persons') ready = Number(state.persons) >= MIN_TRAVELERS;
      else ready = Boolean(state[field]);
      if (!ready) return;
      if (state.step < TOTAL_STEPS) showStep(state.step + 1);
      else requestResults();
    });
    const emailForm = document.getElementById('prepare-email-form');
    if (emailForm) {
      emailForm.addEventListener('submit', (e) => {
        e.preventDefault();
        submitEmailGate(emailForm);
      });
    }
    const emailBack = emailGate.querySelector('.prepare-email-back');
    if (emailBack) {
      emailBack.addEventListener('click', () => {
        hideEmailGate();
        wizard.hidden = false;
        showStep(TOTAL_STEPS);
      });
    }
    const resultsBack = resultsEl.querySelector('.prepare-results-back');
    if (resultsBack) {
      resultsBack.addEventListener('click', () => {
        resultsEl.hidden = true;
        wizard.hidden = false;
        showStep(TOTAL_STEPS);
      });
    }
    resultsEl.querySelector('.prepare-restart').addEventListener('click', () => {
      state.group = null;
      state.persons = null;
      state.style = null;
      state.duration = null;
      state.cities = [];
      renderOptions(step1, catalog.groups, 'group');
      renderTravelersStep(step2);
      renderOptions(step3, catalog.styles, 'style');
      renderOptions(step4, catalog.durations, 'duration');
      if (step5) renderCityOptions(step5);
      hideEmailGate();
      resultsEl.hidden = true;
      wizard.hidden = false;
      showStep(1);
    });
    showStep(1);
  }

  init();
})();
