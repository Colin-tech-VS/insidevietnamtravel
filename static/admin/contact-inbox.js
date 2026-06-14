(function () {
  var list = document.getElementById("contact-mail-list");
  var listWrap = document.querySelector(".contact-mailbox__list-wrap");
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
  var initialLoad = true;

  var IFRAME_CSS =
    "<style>" +
    "html,body{margin:0;padding:14px 16px 20px;max-width:100%!important;overflow-x:hidden!important;" +
    "word-wrap:break-word;overflow-wrap:anywhere;box-sizing:border-box;font-family:system-ui,sans-serif;" +
    "font-size:15px;line-height:1.55;color:#1a1a18;}" +
    "*,*::before,*::after{box-sizing:inherit;max-width:100%;}" +
    "img,svg,video,iframe{max-width:100%!important;height:auto!important;}" +
    "table{width:100%!important;max-width:100%!important;table-layout:fixed;border-collapse:collapse;}" +
    "td,th{word-break:break-word;}" +
    "pre{white-space:pre-wrap;word-break:break-word;overflow-x:hidden;}" +
    "a{word-break:break-word;}" +
    "blockquote{margin:0.75rem 0;padding-left:1rem;border-left:3px solid #ccc;}" +
    "</style>";

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

  function wrapEmailHtml(html) {
    if (!html) return "";
    if (/<head[\s>]/i.test(html)) {
      return html.replace(/<head([^>]*)>/i, "<head$1>" + IFRAME_CSS);
    }
    if (/<html[\s>]/i.test(html)) {
      return html.replace(/<html([^>]*)>/i, "<html$1><head>" + IFRAME_CSS + "</head>");
    }
    return IFRAME_CSS + html;
  }

  function resizeIframe(iframe) {
    if (!iframe) return;
    function fit() {
      try {
        var doc = iframe.contentDocument;
        if (!doc) return;
        var h = Math.max(
          doc.documentElement ? doc.documentElement.scrollHeight : 0,
          doc.body ? doc.body.scrollHeight : 0
        );
        iframe.style.height = Math.max(280, h + 32) + "px";
      } catch (e) {
        iframe.style.minHeight = "420px";
      }
    }
    iframe.addEventListener("load", fit);
    setTimeout(fit, 120);
    setTimeout(fit, 400);
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

  function renderDetail(msgId, options) {
    options = options || {};
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
        ? '    <iframe class="contact-mail-detail__iframe" title="Aperçu email" sandbox="" referrerpolicy="no-referrer" scrolling="no"></iframe>'
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
      var html = wrapEmailHtml(decodeHtml(d.htmlB64));
      if (iframe && html) {
        iframe.srcdoc = html;
        resizeIframe(iframe);
      }

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

    if (options.scrollDetail !== false) {
      detail.scrollTop = 0;
      detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    if (d.read !== "1" && !options.skipMarkRead) {
      markRead(d.id, d.formId || "");
    }
  }

  function closeDetail() {
    activeId = null;
    mailbox.classList.remove("contact-mailbox--open");
    detail.innerHTML =
      '<div class="contact-mail-detail__placeholder">' +
      '<div class="contact-mail-detail__placeholder-icon" aria-hidden="true">✉</div>' +
      "<p>Sélectionnez un filtre ou un message dans la liste</p>" +
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

  function rowMatchesFilter(row, filter) {
    return (
      filter === "all" ||
      (filter === "unread" && row.dataset.read === "0") ||
      row.dataset.source === filter
    );
  }

  function applyFilter(filter, options) {
    options = options || {};
    activeFilter = filter;
    var visible = 0;
    var firstVisible = null;

    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      var show = rowMatchesFilter(row, filter);
      row.hidden = !show;
      if (show) {
        visible++;
        if (!firstVisible) firstVisible = row;
      }
    });

    if (emptyFilter) emptyFilter.hidden = visible > 0;
    if (listWrap) listWrap.scrollTop = 0;

    mailbox.classList.toggle("contact-mailbox--filtered", filter !== "all");

    if (options.openFirst !== false && firstVisible) {
      renderDetail(firstVisible.dataset.id, { scrollDetail: !initialLoad });
    } else if (!firstVisible) {
      closeDetail();
    } else if (activeId) {
      var activeRow = list.querySelector('.contact-mail-row[data-id="' + CSS.escape(activeId) + '"]');
      if (activeRow && activeRow.hidden) {
        if (firstVisible) renderDetail(firstVisible.dataset.id);
        else closeDetail();
      }
    }
  }

  list.addEventListener("click", function (ev) {
    var row = ev.target.closest(".contact-mail-row");
    if (!row || row.hidden) return;
    renderDetail(row.dataset.id);
  });

  list.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    var row = ev.target.closest(".contact-mail-row");
    if (!row || row.hidden) return;
    ev.preventDefault();
    renderDetail(row.dataset.id);
  });

  filterButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filterButtons.forEach(function (b) {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      initialLoad = false;
      applyFilter(btn.dataset.filter, { openFirst: true });
    });
  });

  closeDetail();
})();
