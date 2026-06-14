(function () {
  var list = document.getElementById("contact-mail-list");
  var detail = document.getElementById("contact-mail-detail");
  var mailbox = document.getElementById("contact-mailbox");
  var emptyFilter = document.getElementById("contact-inbox-empty");
  var filterButtons = document.querySelectorAll(".contact-filter__btn");
  var templates = document.querySelectorAll(".contact-mail-template");
  var markReadUrl = mailbox && mailbox.dataset.markReadUrl;

  if (!list || !detail || !mailbox) return;

  var tplById = {};
  templates.forEach(function (tpl) {
    tplById[tpl.dataset.id] = tpl;
  });

  var activeId = null;
  var activeFilter = "all";

  function decodeHtml(b64) {
    if (!b64) return "";
    try {
      return decodeURIComponent(
        Array.prototype.map
          .call(atob(b64), function (c) {
            return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
          })
          .join("")
      );
    } catch (e) {
      return "";
    }
  }

  function setRowReadState(msgId, read) {
    var row = list.querySelector('.contact-mail-row[data-id="' + CSS.escape(msgId) + '"]');
    if (!row) return;
    row.dataset.read = read ? "1" : "0";
    row.classList.toggle("contact-mail-row--unread", !read);
    row.classList.toggle("contact-mail-row--active", row.dataset.id === activeId);
    var dot = row.querySelector(".contact-mail-row__dot");
    if (dot) dot.hidden = read;
  }

  function markRead(msgId, formId) {
    if (!markReadUrl) return;
    fetch(markReadUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ msg_id: msgId, form_id: formId || "" }),
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok) setRowReadState(msgId, true);
      })
      .catch(function () {});
  }

  function renderDetail(msgId) {
    var tpl = tplById[msgId];
    if (!tpl) return;

    var d = tpl.dataset;
    var hasHtml = d.hasHtml === "1";
    var plain = tpl.querySelector(".contact-mail-plain");
    var plainText = plain ? plain.textContent : "";

    detail.innerHTML =
      '<div class="contact-mail-detail">' +
      '  <div class="contact-mail-detail__toolbar">' +
      '    <button type="button" class="btn btn-ghost btn-sm contact-mail-detail__back" id="contact-mail-back">← Liste</button>' +
      '    <div class="contact-mail-detail__actions">' +
      (hasHtml
        ? '      <div class="contact-mail-view-toggle" role="tablist">' +
          '        <button type="button" class="contact-mail-view-toggle__btn is-active" data-view="html">Design HTML</button>' +
          '        <button type="button" class="contact-mail-view-toggle__btn" data-view="plain">Texte</button>' +
          "      </div>"
        : "") +
      '      <a class="btn btn-primary btn-sm contact-mail-detail__reply" href="#">Répondre</a>' +
      '      <form method="post" class="contact-mail-detail__delete" onsubmit="return confirm(\'Supprimer ce message ?\');">' +
      '        <input type="hidden" name="action" value="delete">' +
      '        <input type="hidden" name="msg_id" value="' +
      escapeAttr(d.id) +
      '">' +
      (d.formId ? '<input type="hidden" name="form_id" value="' + escapeAttr(d.formId) + '">' : "") +
      '        <button type="submit" class="btn btn-ghost btn-sm">Supprimer</button>' +
      "      </form>" +
      "    </div>" +
      "  </div>" +
      '  <header class="contact-mail-detail__head">' +
      '    <h3 class="contact-mail-detail__subject">' +
      escapeHtml(d.subject) +
      "</h3>" +
      '    <div class="contact-mail-detail__meta">' +
      '      <span class="contact-source contact-source--' +
      escapeAttr(d.source) +
      '">' +
      escapeHtml(d.sourceLabel) +
      "</span>" +
      (d.lang ? '<span class="contact-msg__lang">' + escapeHtml(d.lang.toUpperCase()) + "</span>" : "") +
      '      <time datetime="' +
      escapeAttr(d.dateIso) +
      '">' +
      escapeHtml(d.date) +
      "</time>" +
      "    </div>" +
      '    <p class="contact-mail-detail__from"><strong>' +
      escapeHtml(d.name) +
      '</strong> &lt;<a href="mailto:' +
      escapeAttr(d.email) +
      '">' +
      escapeHtml(d.email) +
      "</a>&gt;</p>" +
      "  </header>" +
      '  <div class="contact-mail-detail__body">' +
      (hasHtml
        ? '    <iframe class="contact-mail-detail__iframe" title="Aperçu email" sandbox="" referrerpolicy="no-referrer"></iframe>'
        : "") +
      '    <pre class="contact-mail-detail__plain' +
      (hasHtml ? " is-hidden" : "") +
      '"></pre>' +
      "  </div>" +
      "</div>";

    var reply = detail.querySelector(".contact-mail-detail__reply");
    if (reply) {
      reply.href =
        "mailto:" +
        encodeURIComponent(d.email) +
        "?subject=" +
        encodeURIComponent("Re: " + d.subject);
    }

    var plainEl = detail.querySelector(".contact-mail-detail__plain");
    if (plainEl) plainEl.textContent = plainText;

    if (hasHtml) {
      var iframe = detail.querySelector(".contact-mail-detail__iframe");
      var html = decodeHtml(d.htmlB64);
      if (iframe && html) iframe.srcdoc = html;

      var toggles = detail.querySelectorAll(".contact-mail-view-toggle__btn");
      toggles.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var view = btn.dataset.view;
          toggles.forEach(function (b) {
            b.classList.toggle("is-active", b === btn);
          });
          if (iframe) iframe.hidden = view !== "html";
          if (plainEl) plainEl.classList.toggle("is-hidden", view !== "plain");
        });
      });
    }

    var back = detail.querySelector("#contact-mail-back");
    if (back) {
      back.addEventListener("click", function () {
        closeDetail();
      });
    }

    mailbox.classList.add("contact-mailbox--open");
    activeId = msgId;

    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      row.classList.toggle("contact-mail-row--active", row.dataset.id === msgId);
    });

    if (d.read !== "1") {
      markRead(d.id, d.formId || "");
    }
  }

  function closeDetail() {
    activeId = null;
    mailbox.classList.remove("contact-mailbox--open");
    detail.innerHTML =
      '<div class="contact-mail-detail__placeholder">' +
      '<div class="contact-mail-detail__placeholder-icon" aria-hidden="true">✉</div>' +
      "<p>Sélectionnez un message dans la liste</p>" +
      "</div>";
    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      row.classList.remove("contact-mail-row--active");
    });
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(str) {
    return escapeHtml(str).replace(/'/g, "&#39;");
  }

  function applyFilter(filter) {
    activeFilter = filter;
    var visible = 0;
    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      var show =
        filter === "all" ||
        (filter === "unread" && row.dataset.read === "0") ||
        row.dataset.source === filter;
      row.hidden = !show;
      if (show) visible++;
    });
    if (emptyFilter) emptyFilter.hidden = visible > 0;
    if (activeId) {
      var activeRow = list.querySelector('.contact-mail-row[data-id="' + CSS.escape(activeId) + '"]');
      if (activeRow && activeRow.hidden) closeDetail();
    }
  }

  list.addEventListener("click", function (ev) {
    var row = ev.target.closest(".contact-mail-row");
    if (!row) return;
    renderDetail(row.dataset.id);
  });

  list.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    var row = ev.target.closest(".contact-mail-row");
    if (!row) return;
    ev.preventDefault();
    renderDetail(row.dataset.id);
  });

  filterButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filterButtons.forEach(function (b) {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      applyFilter(btn.dataset.filter);
    });
  });

  closeDetail();
})();
