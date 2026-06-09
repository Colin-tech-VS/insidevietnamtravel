(function initBudgetCalculator() {
  'use strict';

  var root = document.getElementById('budget-tool');
  var catalog = window.budgetCatalog;
  var labels = window.budgetLabels || {};
  if (!root || !catalog) return;

  var fxUrl = root.dataset.fxUrl || '/api/fx-rates';
  var fx = { EUR: 1, USD: 1.08, VND: 27500, source: 'fallback' };
  var displayMode = 'eur';

  var els = {
    travellers: document.getElementById('budget-travellers'),
    days: document.getElementById('budget-days'),
    cities: document.getElementById('budget-cities'),
    flights: document.getElementById('budget-flights'),
    scooter: document.getElementById('budget-scooter'),
    guide: document.getElementById('budget-guide'),
    region: document.getElementById('budget-region'),
    meals: document.getElementById('budget-meals'),
    transport: document.getElementById('budget-transport'),
    activities: document.getElementById('budget-activities'),
    oneoffSummary: document.getElementById('budget-oneoff-summary'),
    fxBox: document.getElementById('budget-fx'),
    fxRates: document.getElementById('budget-fx-rates'),
    fxUpdated: document.getElementById('budget-fx-updated'),
    totalVnd: document.getElementById('budget-total-vnd'),
  };

  var locale = (document.documentElement.lang || 'fr').slice(0, 2) === 'en' ? 'en-GB' : 'fr-FR';

  function clampVal(el) {
    var v = parseInt(el.value, 10);
    var min = parseInt(el.min, 10);
    var max = parseInt(el.max, 10);
    if (isNaN(min)) min = 0;
    if (isNaN(max)) max = 999;
    if (isNaN(v)) v = min;
    return Math.min(max, Math.max(min, v));
  }

  function fmtEur(n) {
    return Math.round(n).toLocaleString(locale);
  }

  function fmtVnd(n) {
    return Math.round(n).toLocaleString(locale);
  }

  function selectedPerdayBase() {
    var checked = root.querySelector('input[name="budget-style"]:checked');
    if (!checked) return {};
    try { return JSON.parse(checked.dataset.perday); } catch (e) { return {}; }
  }

  function selectMeta(sel) {
    var opt = sel.options[sel.selectedIndex];
    if (!opt) return {};
    try {
      return {
        mult: JSON.parse(opt.getAttribute('data-mult') || '{}'),
        foodMult: parseFloat(opt.getAttribute('data-food-mult') || '1'),
        transportMult: parseFloat(opt.getAttribute('data-transport-mult') || '1'),
        intercityMult: parseFloat(opt.getAttribute('data-intercity-mult') || '1'),
        activitiesMult: parseFloat(opt.getAttribute('data-activities-mult') || '1'),
      };
    } catch (e) {
      return {};
    }
  }

  function computePerDay() {
    var base = selectedPerdayBase();
    var region = selectMeta(els.region);
    var meals = selectMeta(els.meals);
    var transport = selectMeta(els.transport);
    var acts = selectMeta(els.activities);
    var out = {};
    var keys = ['stay', 'food', 'transport', 'activities', 'misc'];

    keys.forEach(function (k) {
      var v = base[k] || 0;
      if (region.mult && region.mult[k]) v *= region.mult[k];
      if (k === 'food') v *= meals.foodMult || 1;
      if (k === 'transport') v *= transport.transportMult || 1;
      if (k === 'activities') v *= acts.activitiesMult || 1;
      out[k] = Math.round(v * 100) / 100;
    });
    return { perday: out, intercityMult: transport.intercityMult || 1 };
  }

  function selectedOneoffs() {
    var items = [];
    root.querySelectorAll('input[name="budget-oneoff"]:checked').forEach(function (inp) {
      items.push({
        key: inp.value,
        amount: parseFloat(inp.dataset.amount) || 0,
      });
    });
    return items;
  }

  function oneoffPerPerson() {
    return selectedOneoffs().reduce(function (s, o) { return s + o.amount; }, 0);
  }

  function setOut(name, text) {
    root.querySelectorAll('[data-out="' + name + '"]').forEach(function (el) {
      el.textContent = text;
    });
  }

  function formatMoney(eur) {
    if (displayMode === 'both' && fx.VND) {
      return fmtEur(eur) + ' € · ' + fmtVnd(eur * fx.VND) + ' ₫';
    }
    return fmtEur(eur) + ' €';
  }

  function renderFxStrip() {
    if (!els.fxBox || !els.fxRates) return;
    els.fxBox.hidden = false;
    els.fxRates.textContent = '1 € = ' + fmtVnd(fx.VND) + ' ₫ · 1 $ = ' + fmtVnd(fx.USD_VND || (fx.VND / fx.USD)) + ' ₫';
    if (els.fxUpdated) {
      var src = fx.source === 'open.er-api.com' ? (labels.fx_updated || '') : '';
      els.fxUpdated.textContent = src;
    }
  }

  function fetchFx() {
    fetch(fxUrl, { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.VND) {
          fx = {
            EUR: 1,
            USD: data.USD || fx.USD,
            VND: data.VND,
            USD_VND: data.USD_VND || (data.VND / (data.USD || 1)),
            source: data.source || 'api',
            updated_at: data.updated_at,
          };
        }
        renderFxStrip();
        render();
      })
      .catch(function () {
        renderFxStrip();
      });
  }

  function renderOneoffSummary(items, travellers) {
    if (!els.oneoffSummary) return;
    var extras = catalog.extras || {};
    var flights = clampVal(els.flights);
    var scooter = clampVal(els.scooter);
    var guide = clampVal(els.guide);
    var html = '';

    items.forEach(function (o) {
      var cat = (catalog.oneoff || []).find(function (x) { return x.key === o.key; });
      var label = cat ? cat.label : o.key;
      html += '<li><span>' + label + '</span><strong>' + formatMoney(o.amount * travellers) + '</strong></li>';
    });

    if (flights > 0) {
      var fa = (extras.internal_flight || 48) * flights * travellers;
      html += '<li><span>' + (labels.internal_flight || 'Vol intérieur') + ' × ' + flights + '</span><strong>' + formatMoney(fa) + '</strong></li>';
    }
    if (scooter > 0) {
      var sa = (extras.scooter_day || 9) * scooter * travellers;
      html += '<li><span>' + (labels.scooter || 'Scooter') + ' × ' + scooter + ' j</span><strong>' + formatMoney(sa) + '</strong></li>';
    }
    if (guide > 0) {
      var ga = (extras.guide_day || 28) * guide * travellers;
      html += '<li><span>' + (labels.guide || 'Guide') + ' × ' + guide + ' j</span><strong>' + formatMoney(ga) + '</strong></li>';
    }

    els.oneoffSummary.innerHTML = html || '<li class="budget-oneoff--empty"><span>—</span></li>';
  }

  function render() {
    var computed = computePerDay();
    var perday = computed.perday;
    var days = clampVal(els.days);
    var travellers = clampVal(els.travellers);
    var cities = clampVal(els.cities);
    var flights = clampVal(els.flights);
    var scooter = clampVal(els.scooter);
    var guide = clampVal(els.guide);

    [els.days, els.travellers, els.cities, els.flights, els.scooter, els.guide].forEach(function (el) {
      if (el) el.value = clampVal(el);
    });

    var keys = Object.keys(perday);
    var maxCat = Math.max.apply(null, keys.map(function (k) { return perday[k]; }).concat([1]));
    var perdaySum = 0;
    keys.forEach(function (k) { perdaySum += perday[k]; });

    root.querySelectorAll('.budget-bar[data-cat]').forEach(function (bar) {
      var cat = bar.dataset.cat;
      if (cat === 'intercity') return;
      var val = perday[cat] || 0;
      var fill = bar.querySelector('.budget-bar__fill');
      var out = bar.querySelector('[data-out="' + cat + '"]');
      if (fill) fill.style.width = Math.round((val / maxCat) * 100) + '%';
      if (out) out.textContent = formatMoney(val);
    });

    var extras = catalog.extras || {};
    var legs = Math.max(0, cities - 1);
    var intercityPerPerson = legs * (extras.intercity_per_leg || 18) * (computed.intercityMult || 1);
    var intercityBar = root.querySelector('.budget-bar[data-cat="intercity"]');
    if (intercityBar) {
      var iFill = intercityBar.querySelector('.budget-bar__fill');
      if (iFill) iFill.style.width = legs ? '100%' : '8%';
      setOut('intercity', legs ? formatMoney(intercityPerPerson) + ' / pers.' : '—');
    }

    var oneoffItems = selectedOneoffs();
    var oneoffPP = oneoffPerPerson();
    var flightCost = flights * (extras.internal_flight || 48);
    var scooterCost = scooter * (extras.scooter_day || 9);
    var guideCost = guide * (extras.guide_day || 28);

    var perPerson = perdaySum * days + intercityPerPerson + oneoffPP + flightCost + scooterCost + guideCost;
    var total = perPerson * travellers;

    setOut('perday', fmtEur(perdaySum));
    setOut('per_person', fmtEur(perPerson));
    setOut('total', fmtEur(total));

    if (els.totalVnd) {
      if (displayMode === 'both' && fx.VND) {
        els.totalVnd.hidden = false;
        els.totalVnd.textContent = '≈ ' + fmtVnd(total * fx.VND) + ' ₫ · ' + fmtVnd(perPerson * fx.VND) + ' ₫ / pers.';
      } else {
        els.totalVnd.hidden = true;
      }
    }

    renderOneoffSummary(oneoffItems, travellers);

    if (window.ivtProfile && window.ivtProfile.merge) {
      window.ivtProfile.merge({ i: ['budget'], u: ['budget'] });
    }
  }

  root.querySelectorAll('input[name="budget-style"]').forEach(function (i) {
    i.addEventListener('change', render);
  });

  [els.travellers, els.days, els.cities, els.flights, els.scooter, els.guide,
    els.region, els.meals, els.transport, els.activities].forEach(function (el) {
    if (!el) return;
    el.addEventListener('input', render);
    el.addEventListener('change', render);
  });

  root.querySelectorAll('input[name="budget-oneoff"]').forEach(function (inp) {
    inp.addEventListener('change', render);
  });

  root.querySelectorAll('input[name="budget-display"]').forEach(function (inp) {
    inp.addEventListener('change', function () {
      displayMode = inp.value;
      render();
    });
  });

  root.querySelectorAll('.budget-stepper__btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var map = {
        days: els.days,
        travellers: els.travellers,
        cities: els.cities,
        flights: els.flights,
        scooter: els.scooter,
        guide: els.guide,
      };
      var target = map[btn.dataset.step];
      if (!target) return;
      target.value = clampVal(target) + parseInt(btn.dataset.dir, 10);
      render();
    });
  });

  fetchFx();
  render();
})();
