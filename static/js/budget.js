(function () {
  var root = document.getElementById('budget-tool');
  var catalog = window.budgetCatalog;
  if (!root || !catalog) return;

  var styleInputs = root.querySelectorAll('input[name="budget-style"]');
  var travellersEl = document.getElementById('budget-travellers');
  var daysEl = document.getElementById('budget-days');

  function clampVal(el) {
    var v = parseInt(el.value, 10);
    var min = parseInt(el.min, 10) || 1;
    var max = parseInt(el.max, 10) || 999;
    if (isNaN(v)) v = min;
    return Math.min(max, Math.max(min, v));
  }

  function selectedPerday() {
    var checked = root.querySelector('input[name="budget-style"]:checked');
    if (!checked) return {};
    try { return JSON.parse(checked.dataset.perday); } catch (e) { return {}; }
  }

  function oneoffTotal() {
    var total = 0;
    root.querySelectorAll('[data-oneoff]').forEach(function (li) {
      total += parseFloat(li.dataset.oneoff) || 0;
    });
    return total;
  }

  function fmt(n) {
    return Math.round(n).toLocaleString(document.documentElement.lang === 'en' ? 'en-GB' : 'fr-FR');
  }

  function render() {
    var perday = selectedPerday();
    var days = clampVal(daysEl);
    var travellers = clampVal(travellersEl);
    daysEl.value = days;
    travellersEl.value = travellers;

    var keys = Object.keys(perday);
    var maxCat = Math.max.apply(null, keys.map(function (k) { return perday[k]; }).concat([1]));
    var perdaySum = 0;

    keys.forEach(function (k) { perdaySum += perday[k]; });

    root.querySelectorAll('.budget-bar').forEach(function (bar) {
      var cat = bar.dataset.cat;
      var val = perday[cat] || 0;
      var fill = bar.querySelector('.budget-bar__fill');
      var out = bar.querySelector('[data-out="' + cat + '"]');
      if (fill) fill.style.width = Math.round((val / maxCat) * 100) + '%';
      if (out) out.textContent = fmt(val) + ' €';
    });

    var perPerson = perdaySum * days + oneoffTotal();
    var total = perPerson * travellers;

    setOut('perday', fmt(perdaySum));
    setOut('per_person', fmt(perPerson));
    setOut('total', fmt(total));
  }

  function setOut(name, text) {
    root.querySelectorAll('[data-out="' + name + '"]').forEach(function (el) {
      el.textContent = text;
    });
  }

  styleInputs.forEach(function (i) { i.addEventListener('change', render); });
  [travellersEl, daysEl].forEach(function (el) {
    el.addEventListener('input', render);
    el.addEventListener('change', render);
  });

  root.querySelectorAll('.budget-stepper__btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = btn.dataset.step === 'days' ? daysEl : travellersEl;
      var dir = parseInt(btn.dataset.dir, 10);
      target.value = clampVal(target) + dir;
      render();
    });
  });

  render();
})();
