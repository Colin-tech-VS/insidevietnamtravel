(function () {
  "use strict";

  var root = document.getElementById("events-planner-root");
  var timeline = document.getElementById("events-timeline");
  if (!root || !timeline) return;

  var yearSel = document.getElementById("ev-year");
  var monthSel = document.getElementById("ev-month");
  var catSel = document.getElementById("ev-category");
  var upcomingChk = document.getElementById("ev-upcoming");
  var resultEl = document.getElementById("ev-result");
  var emptyEl = document.getElementById("events-empty");
  var today = root.dataset.today || new Date().toISOString().slice(0, 10);
  var msgNone = root.dataset.msgNone || "";
  var msgCount = root.dataset.msgCount || "";

  var cards = Array.prototype.slice.call(timeline.querySelectorAll(".events-card"));
  var yearGroups = Array.prototype.slice.call(timeline.querySelectorAll(".events-year-group"));

  function isVisible(card) {
    var year = yearSel.value;
    var month = monthSel.value;
    var cat = catSel.value;
    var upcomingOnly = upcomingChk && upcomingChk.checked;
    var status = card.dataset.status;
    var recurring = card.dataset.recurring === "1";

    if (year !== "all" && card.dataset.year !== year) return false;
    if (month !== "all" && card.dataset.month !== month) return false;
    if (cat !== "all" && card.dataset.category !== cat) return false;
    if (upcomingOnly && status === "past" && !recurring) return false;
    return true;
  }

  function applyFilters() {
    var visible = 0;
    cards.forEach(function (card) {
      var show = isVisible(card);
      card.hidden = !show;
      if (show) visible += 1;
    });

    yearGroups.forEach(function (group) {
      var groupCards = group.querySelectorAll(".events-card");
      var anyVisible = Array.prototype.some.call(groupCards, function (c) {
        return !c.hidden;
      });
      group.hidden = !anyVisible;
    });

    if (resultEl) {
      if (visible === 0) {
        resultEl.textContent = msgNone;
        resultEl.className = "events-planner__result events-planner__result--empty";
      } else {
        resultEl.textContent = msgCount.replace("{n}", String(visible));
        resultEl.className = "events-planner__result events-planner__result--ok";
      }
    }
    if (emptyEl) emptyEl.hidden = visible > 0;
  }

  function scrollToNext() {
    var target = cards.find(function (card) {
      if (card.hidden) return false;
      var status = card.dataset.status;
      return status === "upcoming" || status === "ongoing" || status === "recurring";
    });
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  [yearSel, monthSel, catSel, upcomingChk].forEach(function (el) {
    if (el) el.addEventListener("change", applyFilters);
  });

  applyFilters();

  if (today >= "2026-01-01") {
    requestAnimationFrame(scrollToNext);
  }
})();
