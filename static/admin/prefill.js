/* Pré-remplissage des formulaires admin via l'URL : ?prefill=1&champ=valeur.
   Utilisé par Linh : ses liens d'action ouvrent une page admin avec le
   formulaire déjà rempli — l'admin vérifie puis valide lui-même. */
(function initAdminPrefill() {
  'use strict';

  var params = new URLSearchParams(window.location.search);
  if (params.get('prefill') !== '1') return;

  var scope = document.querySelector('.admin-main') || document;
  var firstField = null;

  function findFields(name) {
    var escaped = window.CSS && CSS.escape ? CSS.escape(name) : name.replace(/["\\]/g, '');
    return scope.querySelectorAll('form [name="' + escaped + '"]');
  }

  function matchOption(select, value) {
    var target = value.trim().toLowerCase();
    for (var i = 0; i < select.options.length; i++) {
      var o = select.options[i];
      if (o.value === value || o.value.toLowerCase() === target
        || o.textContent.trim().toLowerCase().indexOf(target) === 0) {
        return o;
      }
    }
    return null;
  }

  function fillField(name, value) {
    var fields = findFields(name);
    if (!fields.length) return false;
    var field = fields[0];
    if (field.type === 'radio') {
      field = Array.prototype.filter.call(fields, function (f) { return f.value === value; })[0];
      if (!field) return false;
      field.checked = true;
    } else if (field.type === 'checkbox') {
      field.checked = value === '1' || value === 'true' || value === 'on';
    } else if (field.tagName === 'SELECT') {
      var option = matchOption(field, value);
      if (!option) return false;
      field.value = option.value;
    } else {
      field.value = value;
    }
    field.dispatchEvent(new Event('input', { bubbles: true }));
    field.dispatchEvent(new Event('change', { bubbles: true }));
    if (!firstField) firstField = field;
    return true;
  }

  var filled = 0;
  params.forEach(function (value, key) {
    if (key === 'prefill' || !value) return;
    if (fillField(key, value)) filled++;
  });
  if (!filled || !firstField) return;

  var formEl = firstField.closest('form');
  if (formEl && formEl.parentNode) {
    var notice = document.createElement('p');
    notice.className = 'flash flash--success';
    notice.textContent = '🧭 Formulaire pré-rempli par Linh (' + filled + ' champ' + (filled > 1 ? 's' : '') + ') — vérifiez puis validez.';
    formEl.parentNode.insertBefore(notice, formEl);
  }
  window.requestAnimationFrame(function () {
    firstField.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
})();
