/* Composer Réseaux sociaux — mode page/nouveau, rédaction IA, image, aperçu, UTM. */
(function () {
  "use strict";

  var form = document.getElementById("social-form");
  if (!form) return;

  var fMode = document.getElementById("f-mode");
  var fImage = document.getElementById("f-image-url");
  var fMessage = document.getElementById("f-message");
  var fCampaign = document.getElementById("f-campaign");
  var pageSelect = document.getElementById("page-select");
  var brief = document.getElementById("brief");
  var customImage = document.getElementById("custom-image");
  var customLink = document.getElementById("custom-link");
  var composer = document.getElementById("composer");
  var charCount = document.getElementById("char-count");
  var genBtn = document.getElementById("btn-generate");
  var genStatus = document.getElementById("gen-status");
  var blocks = { page: form.querySelector('[data-block="page"]'), "new": form.querySelector('[data-block="new"]') };

  var preview = document.getElementById("preview");
  var previewImg = document.getElementById("preview-img");
  var previewText = document.getElementById("preview-text");
  var previewLink = document.getElementById("preview-link");

  function sanitizeCampaign(v) {
    v = (v || "").toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "");
    v = v.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    return v || "fb-post";
  }

  function currentMode() {
    var r = form.querySelector('input[name="mode_choice"]:checked');
    return r ? r.value : "page";
  }

  function selectedPageOption() {
    return pageSelect ? pageSelect.options[pageSelect.selectedIndex] : null;
  }

  function defaultCampaign() {
    if (currentMode() === "page") {
      var opt = selectedPageOption();
      return sanitizeCampaign("fb-" + (opt ? opt.value.replace(/:/g, "-") : "page"));
    }
    var d = new Date();
    var ym = "" + d.getFullYear() + ("0" + (d.getMonth() + 1)).slice(-2);
    return sanitizeCampaign("fb-" + ym + "-" + (brief && brief.value ? brief.value.slice(0, 30) : "post"));
  }

  function syncMessage() {
    var text = composer.innerText.replace(/ /g, " ").trim();
    fMessage.value = text;
    charCount.textContent = text.length;
    updatePreview();
  }

  function updatePreview() {
    var text = fMessage.value;
    if (!text) { preview.hidden = true; return; }
    preview.hidden = false;
    previewText.textContent = text;
    var img = fImage.value;
    if (img) { previewImg.src = img; previewImg.hidden = false; } else { previewImg.hidden = true; }
    if (currentMode() === "page") {
      var opt = selectedPageOption();
      var url = opt ? opt.getAttribute("data-url") : "";
      previewLink.hidden = !url;
      previewLink.href = url || "#";
      previewLink.textContent = url || "";
    } else {
      var l = customLink.value.trim();
      previewLink.hidden = !l;
      previewLink.href = l || "#";
      previewLink.textContent = l || "";
    }
  }

  function applyMode() {
    var mode = currentMode();
    fMode.value = mode;
    blocks.page.hidden = mode !== "page";
    blocks["new"].hidden = mode !== "new";
    // image : en mode page, on prend l'image de la page (aperçu OG)
    if (mode === "page") {
      var opt = selectedPageOption();
      fImage.value = opt ? opt.getAttribute("data-image") : "";
    } else {
      fImage.value = customImage.value.trim();
    }
    if (!fCampaign.value.trim()) fCampaign.value = defaultCampaign();
    updatePreview();
  }

  // ── Évènements ──
  form.querySelectorAll('input[name="mode_choice"]').forEach(function (r) {
    r.addEventListener("change", function () { fCampaign.value = defaultCampaign(); applyMode(); });
  });

  if (pageSelect) pageSelect.addEventListener("change", function () {
    fCampaign.value = defaultCampaign();
    applyMode();
  });

  if (customImage) customImage.addEventListener("input", function () {
    clearPoolSelection();
    fImage.value = customImage.value.trim();
    updatePreview();
  });
  if (customLink) customLink.addEventListener("input", updatePreview);

  function clearPoolSelection() {
    document.querySelectorAll(".social-imgpicker__item.is-selected")
      .forEach(function (b) { b.classList.remove("is-selected"); });
  }
  document.querySelectorAll(".social-imgpicker__item").forEach(function (btn) {
    btn.addEventListener("click", function () {
      clearPoolSelection();
      btn.classList.add("is-selected");
      if (customImage) customImage.value = "";
      fImage.value = btn.getAttribute("data-url");
      updatePreview();
    });
  });

  composer.addEventListener("input", syncMessage);
  composer.addEventListener("blur", syncMessage);

  // ── Rédaction IA ──
  if (genBtn) genBtn.addEventListener("click", function () {
    var mode = currentMode();
    var payload = { mode: mode, lang: "fr" };
    if (mode === "page") {
      var opt = selectedPageOption();
      payload.page_id = opt ? opt.value : "";
    } else {
      payload.brief = brief.value.trim();
      if (!payload.brief) { genStatus.textContent = "Indiquez d'abord le sujet."; return; }
    }
    genBtn.disabled = true;
    genStatus.textContent = "Rédaction en cours…";
    fetch(window.SOCIAL_GENERATE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) { return r.json(); }).then(function (data) {
      genBtn.disabled = false;
      if (!data.ok) { genStatus.textContent = data.error || "Échec de la génération."; return; }
      genStatus.textContent = "✓ Texte généré";
      composer.innerText = data.message || "";
      if (data.campaign) fCampaign.value = data.campaign;
      if (mode === "page" && data.image) fImage.value = data.image;
      syncMessage();
    }).catch(function () {
      genBtn.disabled = false;
      genStatus.textContent = "Erreur réseau.";
    });
  });

  // ── Soumission ──
  form.addEventListener("submit", function (e) {
    syncMessage();
    fCampaign.value = sanitizeCampaign(fCampaign.value || defaultCampaign());
    if (!fMessage.value) { e.preventDefault(); alert("Le texte du post est vide."); return; }
    if (currentMode() === "new" && !fImage.value) {
      e.preventDefault();
      alert("Une image est obligatoire pour un contenu nouveau.");
    }
  });

  // Init
  applyMode();
})();
