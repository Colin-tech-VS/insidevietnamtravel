(function () {
  "use strict";

  var root = document.getElementById("season-planner-root");
  if (!root) return;

  var dataEl = document.getElementById("season-planner-data");
  if (!dataEl) return;

  var planner;
  try {
    planner = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }

  var monthSelect = document.getElementById("sp-month");
  var resultEl = document.getElementById("sp-result");
  var calendarEl = document.getElementById("sp-calendar");
  var destInputs = root.querySelectorAll('input[name="dest"]');

  var msgs = {
    pick: root.dataset.msgPick || "Choose destinations and a month.",
    ideal: root.dataset.msgIdeal || "Excellent timing!",
    good: root.dataset.msgGood || "Good period.",
    fair: root.dataset.msgFair || "Fair period.",
    avoid: root.dataset.msgAvoid || "Consider shifting dates.",
  };

  var weights = { ideal: 4, good: 3, fair: 2, avoid: 1 };
  var order = ["ideal", "good", "fair", "avoid"];

  function selectedSlugs() {
    var slugs = [];
    destInputs.forEach(function (inp) {
      if (inp.checked) slugs.push(inp.value);
    });
    return slugs;
  }

  function aggregate(slugs, monthIdx) {
    if (!slugs.length) return null;
    var worst = 4;
    var counts = { ideal: 0, good: 0, fair: 0, avoid: 0 };
    slugs.forEach(function (slug) {
      var dest = planner.destinations && planner.destinations[slug];
      if (!dest || !dest.months) return;
      var rating = dest.months[monthIdx] || "fair";
      counts[rating] = (counts[rating] || 0) + 1;
      worst = Math.min(worst, weights[rating] || 2);
    });
    var verdict = order[4 - worst];
    return { verdict: verdict, counts: counts, slugs: slugs, month: monthIdx };
  }

  function verdictMessage(verdict) {
    return msgs[verdict] || msgs.fair;
  }

  function renderCalendar(slugs) {
    if (!calendarEl || !planner.month_labels) return;
    calendarEl.innerHTML = "";
    calendarEl.setAttribute("aria-hidden", "false");
    var table = document.createElement("table");
    table.className = "season-planner__matrix";
    var thead = document.createElement("thead");
    var hr = document.createElement("tr");
    var th0 = document.createElement("th");
    th0.scope = "col";
    hr.appendChild(th0);
    planner.month_labels.forEach(function (lbl) {
      var th = document.createElement("th");
      th.scope = "col";
      th.textContent = lbl;
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    slugs.forEach(function (slug) {
      var dest = planner.destinations[slug];
      if (!dest) return;
      var tr = document.createElement("tr");
      var th = document.createElement("th");
      th.scope = "row";
      th.textContent = dest.name;
      tr.appendChild(th);
      (dest.months || []).forEach(function (rating, i) {
        var td = document.createElement("td");
        td.className = "season-cell season-cell--" + rating;
        td.title = (planner.month_labels[i] || "") + ": " + rating;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    calendarEl.appendChild(table);
  }

  function update() {
    var slugs = selectedSlugs();
    var monthIdx = parseInt(monthSelect.value, 10) || 0;
    if (!slugs.length) {
      resultEl.className = "season-planner__result season-planner__result--empty";
      resultEl.textContent = msgs.pick;
      if (calendarEl) {
        calendarEl.innerHTML = "";
        calendarEl.setAttribute("aria-hidden", "true");
      }
      return;
    }
    var agg = aggregate(slugs, monthIdx);
    if (!agg) return;
    resultEl.className =
      "season-planner__result season-planner__result--" + agg.verdict;
    resultEl.textContent = verdictMessage(agg.verdict);
    renderCalendar(slugs);
  }

  monthSelect.addEventListener("change", update);
  destInputs.forEach(function (inp) {
    inp.addEventListener("change", update);
  });
  update();
})();
