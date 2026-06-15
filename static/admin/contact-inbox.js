(function () {
  "use strict";

  var list = document.getElementById("contact-mail-list");
  var listWrap = document.querySelector(".contact-mailbox__list-wrap");
  var detail = document.getElementById("contact-mail-detail");
  var mailbox = document.getElementById("contact-mailbox");
  var emptyFilter = document.getElementById("contact-inbox-empty");
  var dataEl = document.getElementById("contact-mails-json");

  if (!list || !detail || !mailbox || !dataEl) return;

  var markReadUrl = mailbox.dataset.markReadUrl || "";
  var replyUrl = mailbox.dataset.replyUrl || "";
  var smtpOk = mailbox.dataset.smtpOk === "1";
  var syncMs = Math.max(60000, parseInt(mailbox.dataset.syncSec || "180", 10) * 1000);

  var messagesById = {};
  try {
    var items = JSON.parse(dataEl.textContent || "[]");
    items.forEach(function (m) {
      if (m && m.id) messagesById[m.id] = m;
    });
  } catch (e) {
    console.error("contact-inbox: JSON invalide", e);
    return;
  }

  var activeId = null;

  var IFRAME_CSS =
    "<style>" +
    "html,body{margin:0;padding:14px 16px 20px;max-width:100%!important;overflow-x:hidden!important;" +
    "overflow-y:auto!important;word-wrap:break-word;overflow-wrap:anywhere;box-sizing:border-box;" +
    "font-family:system-ui,sans-serif;font-size:15px;line-height:1.55;color:#1a1a18;}" +
    "*,*::before,*::after{box-sizing:inherit;max-width:100%;}" +
    "img,svg,video,iframe{max-width:100%!important;height:auto!important;}" +
    "table{width:100%!important;max-width:100%!important;table-layout:fixed;border-collapse:collapse;}" +
    "td,th{word-break:break-word;}" +
    "pre{white-space:pre-wrap;word-break:break-word;overflow-x:hidden;}" +
    "a{word-break:break-word;}" +
    "</style>";

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(String(value));
    }
    return String(value).replace(/[^a-zA-Z0-9_\-]/g, "\\$&");
  }

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

  function findRow(msgId) {
    return list.querySelector('.contact-mail-row[data-id="' + cssEscape(msgId) + '"]');
  }

  function setRowReadState(msgId, read) {
    var row = findRow(msgId);
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

  function replySubject(subject) {
    var s = String(subject || "").trim();
    if (/^(re|fw|fwd|aw|tr|ré|ref)\s*:/i.test(s)) return s;
    return "Re: " + s;
  }

  function renderDetail(msgId) {
    var m = messagesById[msgId];
    if (!m) return;

    var hasHtml = !!m.has_html;
    var plainText = m.message || "";
    var replyDisabled = !smtpOk || !replyUrl || !m.email;

    detail.innerHTML =
      '<div class="contact-mail-detail">' +
      '  <div class="contact-mail-detail__toolbar">' +
      '    <button type="button" class="btn btn-ghost btn-sm contact-mail-detail__back" id="contact-mail-back">← Liste</button>' +
      '    <div class="contact-mail-detail__actions">' +
      (hasHtml
        ? '<div class="contact-mail-view-toggle" role="tablist">' +
          '<button type="button" class="contact-mail-view-toggle__btn is-active" data-view="html">Design HTML</button>' +
          '<button type="button" class="contact-mail-view-toggle__btn" data-view="plain">Texte</button>' +
          "</div>"
        : "") +
      '    <button type="button" class="btn btn-primary btn-sm contact-mail-detail__reply"' +
      (replyDisabled ? " disabled" : "") +
      (replyDisabled && !smtpOk ? ' title="SMTP contact non configuré"' : "") +
      ">Répondre</button>" +
      '    <form method="post" class="contact-mail-detail__delete" onsubmit="return confirm(\'Supprimer ce message ?\');">' +
      '      <input type="hidden" name="action" value="delete">' +
      '      <input type="hidden" name="msg_id" value="' + escapeAttr(m.id) + '">' +
      (m.form_id ? '<input type="hidden" name="form_id" value="' + escapeAttr(m.form_id) + '">' : "") +
      '      <button type="submit" class="btn btn-ghost btn-sm">Supprimer</button>' +
      "    </form>" +
      "    </div>" +
      "  </div>" +
      '  <header class="contact-mail-detail__head">' +
      '    <h3 class="contact-mail-detail__subject">' + escapeHtml(m.subject) + "</h3>" +
      '    <div class="contact-mail-detail__meta">' +
      '      <span class="contact-source contact-source--' + escapeAttr(m.source) + '">' +
      escapeHtml(m.source_label) + "</span>" +
      (m.lang ? '<span class="contact-msg__lang">' + escapeHtml(String(m.lang).toUpperCase()) + "</span>" : "") +
      '      <time datetime="' + escapeAttr(m.created_at || "") + '">' +
      escapeHtml((m.created_at || "").slice(0, 16).replace("T", " ")) +
      "</time>" +
      "    </div>" +
      '    <p class="contact-mail-detail__from"><strong>' + escapeHtml(m.name) + "</strong> &lt;" +
      '<a href="mailto:' + escapeAttr(m.email) + '">' + escapeHtml(m.email) + "</a>&gt;</p>" +
      "  </header>" +
      '  <div class="contact-mail-detail__body">' +
      (hasHtml
        ? '<iframe class="contact-mail-detail__iframe" title="Aperçu email" sandbox="" referrerpolicy="no-referrer"></iframe>'
        : "") +
      '<pre class="contact-mail-detail__plain' + (hasHtml ? " is-hidden" : "") + '"></pre>' +
      '    <div class="contact-reply" id="contact-reply" hidden>' +
      '      <div class="contact-reply__head">' +
      '        <h4 class="contact-reply__title">Répondre</h4>' +
      '        <p class="contact-reply__status" id="contact-reply-status" hidden></p>' +
      "      </div>" +
      '      <label class="contact-reply__field">' +
      '        <span class="contact-reply__label">À</span>' +
      '        <input type="email" class="contact-reply__input" id="contact-reply-to" readonly value="' +
      escapeAttr(m.email) + '">' +
      "      </label>" +
      '      <label class="contact-reply__field">' +
      '        <span class="contact-reply__label">Objet</span>' +
      '        <input type="text" class="contact-reply__input" id="contact-reply-subject" value="' +
      escapeAttr(replySubject(m.subject)) + '">' +
      "      </label>" +
      '      <label class="contact-reply__field contact-reply__field--grow">' +
      '        <span class="contact-reply__label">Message</span>' +
      '        <textarea class="contact-reply__textarea" id="contact-reply-body" rows="8" placeholder="Votre réponse…"></textarea>' +
      "      </label>" +
      '      <div class="contact-reply__actions">' +
      '        <button type="button" class="btn btn-primary btn-sm" id="contact-reply-send">Envoyer</button>' +
      '        <button type="button" class="btn btn-ghost btn-sm" id="contact-reply-cancel">Annuler</button>' +
      "      </div>" +
      "    </div>" +
      "  </div>" +
      "</div>";

    var plainEl = detail.querySelector(".contact-mail-detail__plain");
    if (plainEl) plainEl.textContent = plainText;

    if (hasHtml) {
      var iframe = detail.querySelector(".contact-mail-detail__iframe");
      var html = wrapEmailHtml(decodeHtml(m.message_html_b64 || ""));
      if (iframe && html) iframe.srcdoc = html;

      var toggles = detail.querySelectorAll(".contact-mail-view-toggle__btn");
      toggles.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var view = btn.getAttribute("data-view");
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
      back.addEventListener("click", function (e) {
        e.preventDefault();
        closeDetail();
      });
    }

    var replyPanel = detail.querySelector("#contact-reply");
    var replyBtn = detail.querySelector(".contact-mail-detail__reply");
    var replySend = detail.querySelector("#contact-reply-send");
    var replyCancel = detail.querySelector("#contact-reply-cancel");
    var replyBody = detail.querySelector("#contact-reply-body");
    var replyStatus = detail.querySelector("#contact-reply-status");

    function setReplyOpen(open) {
      if (!replyPanel) return;
      replyPanel.hidden = !open;
      if (replyBtn) replyBtn.classList.toggle("is-active", open);
      if (open && replyBody) {
        replyBody.focus();
        replyPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }

    function setReplyStatus(text, kind) {
      if (!replyStatus) return;
      if (!text) {
        replyStatus.hidden = true;
        replyStatus.textContent = "";
        replyStatus.className = "contact-reply__status";
        return;
      }
      replyStatus.hidden = false;
      replyStatus.textContent = text;
      replyStatus.className = "contact-reply__status contact-reply__status--" + (kind || "info");
    }

    if (replyBtn) {
      replyBtn.addEventListener("click", function (e) {
        e.preventDefault();
        if (replyBtn.disabled) return;
        setReplyOpen(replyPanel && replyPanel.hidden);
      });
    }

    if (replyCancel) {
      replyCancel.addEventListener("click", function () {
        setReplyOpen(false);
        setReplyStatus("");
      });
    }

    if (replySend) {
      replySend.addEventListener("click", function () {
        if (!replyUrl) return;
        var bodyVal = replyBody ? replyBody.value.trim() : "";
        var subjectEl = detail.querySelector("#contact-reply-subject");
        var subjectVal = subjectEl ? subjectEl.value.trim() : replySubject(m.subject);
        if (bodyVal.length < 2) {
          setReplyStatus("Écrivez un message (au moins 2 caractères).", "error");
          if (replyBody) replyBody.focus();
          return;
        }
        replySend.disabled = true;
        if (replyCancel) replyCancel.disabled = true;
        setReplyStatus("Envoi en cours…", "info");
        fetch(replyUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            to_email: m.email,
            subject: subjectVal,
            body: bodyVal,
            message_id: m.message_id || "",
            in_reply_to: m.in_reply_to || "",
            references: m.references || "",
          }),
        })
          .then(function (r) {
            return r.json().then(function (data) {
              return { ok: r.ok, data: data };
            });
          })
          .then(function (res) {
            if (res.data && res.data.ok) {
              setReplyStatus("Réponse envoyée à " + (res.data.to || m.email) + ".", "success");
              if (replyBody) replyBody.value = "";
              if (replySend) replySend.textContent = "Envoyé";
            } else {
              setReplyStatus((res.data && res.data.error) || "Échec de l'envoi.", "error");
              replySend.disabled = false;
              if (replyCancel) replyCancel.disabled = false;
            }
          })
          .catch(function () {
            setReplyStatus("Erreur réseau lors de l'envoi.", "error");
            replySend.disabled = false;
            if (replyCancel) replyCancel.disabled = false;
          });
      });
    }

    mailbox.classList.add("contact-mailbox--open");
    activeId = msgId;

    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      row.classList.toggle("contact-mail-row--active", row.dataset.id === msgId);
    });

    detail.scrollTop = 0;
    var body = detail.querySelector(".contact-mail-detail__body");
    if (body) body.scrollTop = 0;

    if (!m.read) {
      m.read = true;
      markRead(m.id, m.form_id || "");
      setRowReadState(m.id, true);
    }
  }

  function closeDetail() {
    activeId = null;
    mailbox.classList.remove("contact-mailbox--open");
    var syncPending = document.getElementById("contact-sync-pending");
    if (syncPending) syncPending.hidden = true;
    detail.innerHTML =
      '<div class="contact-mail-detail__placeholder">' +
      '<div class="contact-mail-detail__placeholder-icon" aria-hidden="true">✉</div>' +
      "<p>Cliquez un message dans la liste pour le lire</p>" +
      "</div>";
    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      row.classList.remove("contact-mail-row--active");
    });
  }

  function rowMatchesFilter(row, filter) {
    if (filter === "all") return true;
    if (filter === "unread") return row.getAttribute("data-read") === "0";
    return row.getAttribute("data-source") === filter;
  }

  function applyFilter(filter) {
    var visible = 0;
    list.querySelectorAll(".contact-mail-row").forEach(function (row) {
      var show = rowMatchesFilter(row, filter);
      row.classList.toggle("is-filtered-out", !show);
      row.hidden = !show;
      if (show) visible++;
    });
    if (emptyFilter) emptyFilter.hidden = visible > 0;
    if (listWrap) listWrap.scrollTop = 0;
    mailbox.classList.toggle("contact-mailbox--filtered", filter !== "all");

    if (activeId) {
      var activeRow = findRow(activeId);
      if (!activeRow || activeRow.hidden || activeRow.classList.contains("is-filtered-out")) {
        closeDetail();
      }
    }
  }

  list.addEventListener("click", function (ev) {
    var row = ev.target.closest(".contact-mail-row");
    if (!row || row.hidden || row.classList.contains("is-filtered-out")) return;
    ev.preventDefault();
    renderDetail(row.getAttribute("data-id"));
  });

  list.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    var row = ev.target.closest(".contact-mail-row");
    if (!row || row.hidden || row.classList.contains("is-filtered-out")) return;
    ev.preventDefault();
    renderDetail(row.getAttribute("data-id"));
  });

  document.querySelectorAll(".contact-filter__btn").forEach(function (btn) {
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      var filter = btn.getAttribute("data-filter") || "all";
      document.querySelectorAll(".contact-filter__btn").forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
      applyFilter(filter);
    });
  });

  var syncBtn = document.getElementById("contact-sync-btn");
  if (syncBtn) {
    syncBtn.addEventListener("click", function () {
      window.location.reload();
    });
  }

  window.setInterval(function () {
    if (mailbox.classList.contains("contact-mailbox--open")) {
      var pending = document.getElementById("contact-sync-pending");
      if (pending) pending.hidden = false;
      return;
    }
    window.location.reload();
  }, syncMs);

  closeDetail();
})();
