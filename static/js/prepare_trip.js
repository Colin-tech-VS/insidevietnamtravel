(function () {
  const catalog = window.prepareTripCatalog;
  if (!catalog) return;

  const wizard = document.getElementById('prepare-wizard');
  const resultsEl = document.getElementById('prepare-results');
  if (!wizard || !resultsEl) return;

  const state = { group: null, style: null, duration: null, step: 1 };
  const labels = catalog.labels || {};

  function uniq(arr) {
    return [...new Set(arr)];
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
    return {
      itinSlugs,
      destSlugs: profile.destination_slugs || [],
      artSlugs: profile.article_slugs || [],
      catKeys: profile.categories || [],
    };
  }

  function renderOptions(container, items, field) {
    container.innerHTML = items.map((item) => (
      `<button type="button" class="prepare-option${state[field] === item.id ? ' is-selected' : ''}" data-value="${item.id}" data-field="${field}">
        <span class="prepare-option__label">${item.label}</span>
        ${item.desc ? `<span class="prepare-option__desc">${item.desc}</span>` : ''}
      </button>`
    )).join('');
    container.querySelectorAll('.prepare-option').forEach((btn) => {
      btn.addEventListener('click', () => {
        state[field] = btn.dataset.value;
        container.querySelectorAll('.prepare-option').forEach((b) => b.classList.remove('is-selected'));
        btn.classList.add('is-selected');
      });
    });
  }

  function showStep(n) {
    state.step = n;
    wizard.querySelectorAll('.prepare-step').forEach((el) => {
      const active = Number(el.dataset.step) === n;
      el.classList.toggle('is-active', active);
      el.hidden = !active;
    });
    wizard.querySelectorAll('.prepare-wizard__dot').forEach((dot) => {
      dot.classList.toggle('is-active', Number(dot.dataset.step) <= n);
    });
    const back = wizard.querySelector('.prepare-back');
    const next = wizard.querySelector('.prepare-next');
    if (back) back.hidden = n === 1;
    if (next) next.textContent = n === 3 ? labels.results_title || 'Results' : (labels.next || 'Continue');
  }

  function cardHtml(item, type) {
    if (type === 'itin') {
      return `<a href="${item.url}" class="prepare-card prepare-card--itin">
        <span class="prepare-card__meta">${item.duration} ${(catalog.labels && catalog.labels.days) || 'days'}</span>
        <h3>${item.title}</h3>
        <p>${item.summary}</p>
        <span class="prepare-card__hint">${item.budget_hint || ''}</span>
      </a>`;
    }
    if (type === 'dest') {
      return `<a href="${item.url}" class="prepare-card prepare-card--dest">
        <h3>${item.name}</h3>
        <p>${item.tagline}</p>
      </a>`;
    }
    if (type === 'art') {
      return `<a href="${item.url}" class="prepare-card prepare-card--art">
        <span class="prepare-card__meta">${item.category_label}</span>
        <h3>${item.title}</h3>
        <p>${item.excerpt}</p>
      </a>`;
    }
    return `<a href="${item.url}" class="prepare-card prepare-card--cat">
      <h3>${item.label}</h3>
      <p>${item.description}</p>
    </a>`;
  }

  function renderResults() {
    const { itinSlugs, destSlugs, artSlugs, catKeys } = resolveSlugs();
    const articles = catalog.articles || {};
    const extraArts = Object.values(articles).filter(
      (a) => catKeys.includes(a.category) && !artSlugs.includes(a.slug),
    ).slice(0, 4);

    const sections = [];
    const itins = itinSlugs.map((s) => catalog.itineraries[s]).filter(Boolean);
    if (itins.length) {
      sections.push(`<section class="prepare-results__block"><h3>${labels.itin_section}</h3><div class="prepare-cards">${itins.map((i) => cardHtml(i, 'itin')).join('')}</div></section>`);
    }
    const dests = destSlugs.map((s) => catalog.destinations[s]).filter(Boolean);
    if (dests.length) {
      sections.push(`<section class="prepare-results__block"><h3>${labels.dest_section}</h3><div class="prepare-cards">${dests.map((d) => cardHtml(d, 'dest')).join('')}</div></section>`);
    }
    const arts = artSlugs.map((s) => articles[s]).filter(Boolean).concat(extraArts);
    if (arts.length) {
      sections.push(`<section class="prepare-results__block"><h3>${labels.art_section}</h3><div class="prepare-cards">${arts.map((a) => cardHtml(a, 'art')).join('')}</div></section>`);
    }
    const cats = catKeys.map((k) => catalog.categories[k]).filter(Boolean);
    if (cats.length) {
      sections.push(`<section class="prepare-results__block"><h3>${labels.cat_section}</h3><div class="prepare-cards">${cats.map((c) => cardHtml(c, 'cat')).join('')}</div></section>`);
    }

    resultsEl.querySelector('.prepare-results__title').textContent = labels.results_title || '';
    resultsEl.querySelector('.prepare-results__sub').textContent = labels.results_sub || '';
    resultsEl.querySelector('.prepare-restart').textContent = labels.restart || '';
    resultsEl.querySelector('.prepare-pdf-cta').textContent = labels.pdf_cta || '';
    resultsEl.querySelector('.prepare-results__sections').innerHTML = sections.join('') || `<p class="muted">${labels.empty || ''}</p>`;

    wizard.hidden = true;
    resultsEl.hidden = false;
    resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function init() {
    const step1 = wizard.querySelector('[data-step="1"] .prepare-options');
    const step2 = wizard.querySelector('[data-step="2"] .prepare-options');
    const step3 = wizard.querySelector('[data-step="3"] .prepare-options');
    renderOptions(step1, catalog.groups, 'group');
    renderOptions(step2, catalog.styles, 'style');
    renderOptions(step3, catalog.durations, 'duration');

    wizard.querySelector('.prepare-back').addEventListener('click', () => showStep(state.step - 1));
    wizard.querySelector('.prepare-next').addEventListener('click', () => {
      const field = state.step === 1 ? 'group' : state.step === 2 ? 'style' : 'duration';
      if (!state[field]) return;
      if (state.step < 3) showStep(state.step + 1);
      else renderResults();
    });
    resultsEl.querySelector('.prepare-restart').addEventListener('click', () => {
      state.group = null;
      state.style = null;
      state.duration = null;
      renderOptions(step1, catalog.groups, 'group');
      renderOptions(step2, catalog.styles, 'style');
      renderOptions(step3, catalog.durations, 'duration');
      resultsEl.hidden = true;
      wizard.hidden = false;
      showStep(1);
    });
    showStep(1);
  }

  init();
})();
