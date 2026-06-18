/**
 * Éditeurs WYSIWYG style Word pour les formulaires manuels admin.
 */
(function () {
  const CONTENT_CSS = '/static/admin/wysiwyg-content.css';
  let initialized = false;

  const BASE = {
    license_key: 'gpl',
    language: 'fr_FR',
    language_url: 'https://cdn.jsdelivr.net/npm/tinymce-i18n@24.12.30/langs7/fr_FR.js',
    skin: 'oxide',
    content_css: CONTENT_CSS,
    branding: false,
    promotion: false,
    resize: true,
    statusbar: true,
    elementpath: false,
    paste_as_text: false,
    convert_urls: false,
    entity_encoding: 'raw',
    setup(editor) {
      editor.on('change input undo redo', () => editor.save());
    },
  };

  const CONFIGS = [
    {
      selector: '.wysiwyg-editor--full',
      ...BASE,
      min_height: 420,
      plugins: [
        'advlist', 'autolink', 'lists', 'link', 'charmap',
        'searchreplace', 'visualblocks', 'code', 'wordcount', 'autoresize',
      ],
      toolbar:
        'undo redo | blocks fontsize | bold italic underline strikethrough | forecolor | ' +
        'alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | ' +
        'link | removeformat code',
      menubar: 'edit view insert format tools',
      block_formats: 'Paragraphe=p; Titre 2=h2; Titre 3=h3; Titre 4=h4',
      font_size_formats: '10pt 11pt 12pt 14pt 16pt 18pt 24pt',
      autoresize_bottom_margin: 32,
    },
    {
      selector: '.wysiwyg-editor--compact',
      ...BASE,
      min_height: 90,
      max_height: 140,
      plugins: ['autoresize', 'wordcount'],
      toolbar: 'bold italic | removeformat',
      menubar: false,
      autoresize_bottom_margin: 12,
    },
    {
      selector: '.wysiwyg-editor--list',
      ...BASE,
      min_height: 200,
      plugins: ['lists', 'autolink', 'wordcount', 'autoresize'],
      toolbar: 'undo redo | bold italic | bullist numlist | removeformat',
      menubar: false,
      autoresize_bottom_margin: 20,
    },
  ];

  function bindFormSave() {
    const selector = '#guide-form-manual, #dest-form-manual, #newsletter-form-manual, form:has(.wysiwyg-editor)';
    document.querySelectorAll(selector).forEach((form) => {
      form.addEventListener('submit', (e) => {
        if (window.tinymce) {
          tinymce.triggerSave();
        }

        let invalid = false;
        form.querySelectorAll('.wysiwyg-editor[required]').forEach((ta) => {
          const plain = (ta.value || '').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim();
          if (!plain) {
            ta.setCustomValidity('Ce champ est obligatoire.');
            invalid = true;
          } else {
            ta.setCustomValidity('');
          }
        });

        if (invalid || !form.checkValidity()) {
          e.preventDefault();
          form.reportValidity();
        }
      });
    });
  }

  function refreshEditors() {
    if (!window.tinymce) return;
    tinymce.editors.forEach((ed) => {
      ed.fire('ResizeEditor');
    });
  }

  function initEditors() {
    if (initialized || !window.tinymce) return;
    const hasAny = document.querySelector('.wysiwyg-editor');
    if (!hasAny) return;

    initialized = true;
    CONFIGS.forEach((cfg) => {
      if (document.querySelector(cfg.selector)) {
        tinymce.init(cfg);
      }
    });
    bindFormSave();
  }

  function onManualTabOpen() {
    if (!initialized) {
      initEditors();
    } else {
      setTimeout(refreshEditors, 80);
    }
  }

  // ── Init paresseux par élément (pages sans onglets, ex. Partenaires recommandés) ──
  // Évite d'initialiser des DIZAINES d'éditeurs TinyMCE d'un coup au chargement
  // (ce qui fige l'onglet) : on n'initialise un éditeur QUE lorsque son <details>
  // est ouvert.
  function _configFor(el) {
    if (el.classList.contains('wysiwyg-editor--compact')) return CONFIGS[1];
    if (el.classList.contains('wysiwyg-editor--list')) return CONFIGS[2];
    return CONFIGS[0];
  }

  function initEl(el) {
    if (!window.tinymce || el.dataset.wysiwygInit) return;
    el.dataset.wysiwygInit = '1';
    const cfg = { ..._configFor(el), target: el };
    delete cfg.selector;
    tinymce.init(cfg);
  }

  function lazyWatch() {
    // Éditeurs visibles (hors <details> fermé) : init immédiat.
    document.querySelectorAll('.wysiwyg-editor').forEach((el) => {
      const d = el.closest('details');
      if (!d || d.open) initEl(el);
    });
    // Sinon, init à l'ouverture du <details>.
    document.querySelectorAll('details').forEach((d) => {
      d.addEventListener('toggle', () => {
        if (d.open) d.querySelectorAll('.wysiwyg-editor').forEach(initEl);
      });
    });
  }

  function watchTabs() {
    const hasTabs = !!document.querySelector('.content-tab');

    document.querySelectorAll('.content-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        if (tab.dataset.tab === 'manual') {
          setTimeout(onManualTabOpen, 60);
        }
      });
    });

    const manualPanel = document.getElementById('tab-manual');
    if (manualPanel && !manualPanel.hidden) {
      onManualTabOpen();
    }

    // Pages sans onglets : init paresseux par <details> (perf).
    if (!hasTabs) {
      lazyWatch();
      bindFormSave();
    }
  }

  function loadTinyMCE() {
    if (window.tinymce) {
      watchTabs();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/tinymce@7.6.1/tinymce.min.js';
    script.onload = watchTabs;
    document.head.appendChild(script);
  }

  document.addEventListener('DOMContentLoaded', loadTinyMCE);
})();
