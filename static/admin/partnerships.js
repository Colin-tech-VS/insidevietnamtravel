/* Partenariats — recherche IA d'influenceurs (job en arrière-plan + suivi). */
(function () {
  "use strict";

  var btn = document.getElementById("partner-search-btn");
  var brief = document.getElementById("partner-search-brief");
  var status = document.getElementById("partner-search-status");
  if (!btn || !brief || !status) return;

  var polling = null;

  function show(msg, isError) {
    status.hidden = false;
    status.textContent = msg;
    status.classList.toggle("social-hint--warn", !!isError);
  }

  function done(msg, isError) {
    if (polling) { clearInterval(polling); polling = null; }
    btn.disabled = false;
    show(msg, isError);
  }

  function poll(token) {
    polling = setInterval(function () {
      fetch(window.PARTNER_JOB_URL.replace("__TOKEN__", encodeURIComponent(token)), {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === "running") {
            if (data.phase) show("⏳ " + data.phase);
            return;
          }
          if (data.status === "done") {
            var names = (data.names || []).join(" · ");
            done("✅ " + (data.message || "Recherche terminée.") + (names ? " — " + names : ""));
            // Recharge pour afficher les nouveaux contacts dans la liste.
            setTimeout(function () { window.location.reload(); }, 1800);
            return;
          }
          done("✗ " + (data.error || "Recherche interrompue."), true);
        })
        .catch(function () { /* erreur réseau passagère : on continue le polling */ });
    }, 2000);
  }

  btn.addEventListener("click", function () {
    var value = brief.value.trim();
    if (!value) {
      show("Décrivez d'abord la recherche (ex. « influenceurs francophones voyage Vietnam »).", true);
      brief.focus();
      return;
    }
    btn.disabled = true;
    show("⏳ Lancement de la recherche…");
    fetch(window.PARTNER_SEARCH_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ brief: value }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { done("✗ " + (data.error || "Échec du lancement."), true); return; }
        poll(data.job_token);
      })
      .catch(function () { done("✗ Erreur réseau.", true); });
  });

  brief.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); btn.click(); }
  });
})();
