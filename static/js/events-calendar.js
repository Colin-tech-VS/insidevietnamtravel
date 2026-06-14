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
  var modal = document.getElementById("events-modal");
  var modalContent = document.getElementById("events-modal-content");
  var today = root.dataset.today || new Date().toISOString().slice(0, 10);
  var msgNone = root.dataset.msgNone || "";
  var msgCount = root.dataset.msgCount || "";
  var labels = {
    highlights: root.dataset.lblHighlights || "",
    detail: root.dataset.lblDetail || "",
    practical: root.dataset.lblPractical || "",
    regions: root.dataset.lblRegions || "",
    destinations: root.dataset.lblDestinations || "",
    tip: root.dataset.lblTip || "",
    mustSee: root.dataset.lblMustSee || "",
  };

  var dataEl = document.getElementById("events-calendar-data");
  var eventsById = {};
  if (dataEl) {
    try {
      JSON.parse(dataEl.textContent || "[]").forEach(function (ev) {
        eventsById[ev.id] = ev;
      });
    } catch (e) { /* ignore */ }
  }

  var cards = Array.prototype.slice.call(
    document.querySelectorAll("[data-event-open], .events-card")
  );
  var yearGroups = Array.prototype.slice.call(timeline.querySelectorAll(".events-year-group"));
  var lastFocus = null;

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
      if (!card.dataset.year) return;
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

  function esc(text) {
    var d = document.createElement("div");
    d.textContent = text == null ? "" : String(text);
    return d.innerHTML;
  }

  function listHtml(items) {
    if (!items || !items.length) return "";
    return "<ul class=\"events-modal__list\">" +
      items.map(function (item) { return "<li>" + esc(item) + "</li>"; }).join("") +
      "</ul>";
  }

  function badgesHtml(ev) {
    var html = "<span class=\"events-modal__badge events-modal__badge--" + esc(ev.category) + "\">" +
      esc(ev.category_label) + "</span>";
    if (ev.must_see) {
      html += "<span class=\"events-modal__badge events-modal__badge--star\">" +
        esc(labels.mustSee) + "</span>";
    }
    if (ev.status_label) {
      html += "<span class=\"events-modal__badge events-modal__badge--" + esc(ev.status) + "\">" +
        esc(ev.status_label) + "</span>";
    }
    return html;
  }

  function openModal(id) {
    var ev = eventsById[id];
    if (!ev || !modal || !modalContent) return;

    lastFocus = document.activeElement;

    var destsHtml = "";
    if (ev.destinations && ev.destinations.length) {
      destsHtml = "<div class=\"events-modal__dests\">" +
        ev.destinations.map(function (d) {
          return "<a class=\"events-modal__dest\" href=\"" + esc(d.url) + "\">" +
            esc(d.name) + "</a>";
        }).join("") + "</div>";
    }

    var lunar = ev.lunar_note
      ? "<span class=\"events-modal__lunar\">" + esc(ev.lunar_note) + "</span>"
      : "";

    modalContent.innerHTML =
      "<figure class=\"events-modal__hero\">" +
        "<img class=\"events-modal__img\" src=\"" + esc(ev.image_hd || ev.image) + "\" " +
        "alt=\"" + esc(ev.image_alt) + "\" width=\"960\" height=\"540\" loading=\"eager\">" +
        "<span class=\"events-modal__hero-icon\" aria-hidden=\"true\">" + esc(ev.icon) + "</span>" +
      "</figure>" +
      "<div class=\"events-modal__body\">" +
        "<div class=\"events-modal__badges\">" + badgesHtml(ev) + "</div>" +
        "<h2 class=\"events-modal__title\" id=\"events-modal-title\">" + esc(ev.title) + "</h2>" +
        "<div class=\"events-modal__datebar\">" +
          "<time datetime=\"" + esc(ev.start_date) + "\">" + esc(ev.date_label) + "</time>" +
          lunar +
        "</div>" +
        "<p class=\"events-modal__summary\">" + esc(ev.summary) + "</p>" +
        (ev.highlights && ev.highlights.length
          ? "<section class=\"events-modal__section\">" +
              "<h3 class=\"events-modal__section-title\">" + esc(labels.highlights) + "</h3>" +
              listHtml(ev.highlights) +
            "</section>"
          : "") +
        (ev.experience
          ? "<section class=\"events-modal__section\">" +
              "<h3 class=\"events-modal__section-title\">" + esc(labels.detail) + "</h3>" +
              "<p class=\"events-modal__text\">" + esc(ev.experience) + "</p>" +
            "</section>"
          : "") +
        (ev.practical && ev.practical.length
          ? "<section class=\"events-modal__section\">" +
              "<h3 class=\"events-modal__section-title\">" + esc(labels.practical) + "</h3>" +
              listHtml(ev.practical) +
            "</section>"
          : "") +
        (ev.region_labels && ev.region_labels.length
          ? "<p class=\"events-modal__meta\">" +
              "<strong>" + esc(labels.regions) + "</strong> " +
              esc(ev.region_labels.join(" · ")) +
            "</p>"
          : "") +
        (destsHtml
          ? "<div class=\"events-modal__meta-block\">" +
              "<strong class=\"events-modal__meta-label\">" + esc(labels.destinations) + "</strong>" +
              destsHtml +
            "</div>"
          : "") +
        (ev.tip
          ? "<aside class=\"events-modal__tip\">" +
              "<strong>" + esc(labels.tip) + "</strong> " + esc(ev.tip) +
            "</aside>"
          : "") +
      "</div>";

    modal.hidden = false;
    document.body.classList.add("events-modal-open");
    modalContent.scrollTop = 0;

    var closeBtn = modal.querySelector(".events-modal__close");
    if (closeBtn) closeBtn.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("events-modal-open");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("click", function (e) {
    var trigger = e.target.closest("[data-event-open]");
    if (trigger) {
      e.preventDefault();
      openModal(trigger.getAttribute("data-event-open"));
      return;
    }
    if (e.target.closest("[data-events-modal-close]")) {
      closeModal();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal && !modal.hidden) {
      closeModal();
    }
  });

  [yearSel, monthSel, catSel, upcomingChk].forEach(function (el) {
    if (el) el.addEventListener("change", applyFilters);
  });

  applyFilters();

  var hash = window.location.hash.replace(/^#event-/, "");
  if (hash && eventsById[hash]) {
    openModal(hash);
  }
})();
