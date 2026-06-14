(function () {
  "use strict";

  var revealEls = document.querySelectorAll(".partner-reveal, .partner-vitrine-highlight-card, .partner-vitrine-related-card, .partner-directory__card");
  if (revealEls.length && "IntersectionObserver" in window) {
    revealEls.forEach(function (el) {
      el.classList.add("partner-reveal--pending");
    });
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("partner-reveal--visible");
          observer.unobserve(entry.target);
        });
      },
      { root: null, rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    revealEls.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    revealEls.forEach(function (el) {
      el.classList.add("partner-reveal--visible");
    });
  }

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
