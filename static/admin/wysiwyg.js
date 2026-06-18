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
    document.querySelectorAll('#guide-form-manual, #dest-form-manual, #newsletter-form-manual').forEach((form) => {
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

  function watchTabs() {
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

    // Pages sans onglets (ex. Partenaires recommandés) : initialise directement
    // les éditeurs présents, même à l'intérieur de <details> fermés.
    if (!document.querySelector('.content-tab')) {
      initEditors();
    }
    // Quand un <details> contenant un éditeur s'ouvre, (ré)initialise / redimensionne.
    document.querySelectorAll('details').forEach((d) => {
      d.addEventListener('toggle', () => {
        if (!d.open) return;
        if (!initialized) initEditors();
        else setTimeout(refreshEditors, 80);
      });
    });
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
