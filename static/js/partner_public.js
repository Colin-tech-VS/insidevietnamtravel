(function () {
  "use strict";

  function setupReveal(selector) {
    var revealEls = document.querySelectorAll(selector);
    if (!revealEls.length) return;
    if ("IntersectionObserver" in window) {
      revealEls.forEach(function (el) {
        el.classList.add("partner-reveal--pending");
      });
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("partner-reveal--visible");
            entry.target.classList.remove("partner-reveal--pending");
            observer.unobserve(entry.target);
          });
        },
        { root: null, rootMargin: "0px 0px -4% 0px", threshold: 0.05 }
      );
      revealEls.forEach(function (el) {
        observer.observe(el);
      });
    } else {
      revealEls.forEach(function (el) {
        el.classList.add("partner-reveal--visible");
        el.classList.remove("partner-reveal--pending");
      });
    }
  }

  // Sections uniquement — pas les cartes à l'intérieur (sinon opacity 0 sur les points forts).
  setupReveal(".partner-reveal");
  setupReveal(".partner-directory__card");

  var filters = document.querySelectorAll(".partner-directory__filter");
  var cards = document.querySelectorAll(".partner-directory__card");
  if (filters.length && cards.length) {
    filters.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var type = btn.getAttribute("data-filter") || "all";
        filters.forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });
        cards.forEach(function (card) {
          var show = type === "all" || card.getAttribute("data-type") === type;
          card.classList.toggle("partner-directory__card--hidden", !show);
          if (show) {
            card.classList.add("partner-reveal--visible");
          }
        });
      });
    });
  }
})();
