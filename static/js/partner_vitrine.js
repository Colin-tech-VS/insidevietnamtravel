document.addEventListener('DOMContentLoaded', () => {
  const fieldsRoot = document.getElementById('partner-hl-fields');
  const addBtn = document.getElementById('partner-hl-add');
  const countEl = document.getElementById('vitrine-hl-count');
  const fillEl = document.getElementById('vitrine-hl-fill');
  const meterEl = document.getElementById('vitrine-hl-meter');
  const minHintEl = document.getElementById('vitrine-hl-min-hint');
  const statusEl = document.getElementById('vitrine-hl-status');
  const previewWrap = document.getElementById('vitrine-hl-preview');
  const previewList = document.getElementById('vitrine-hl-preview-list');
  const meterTrack = meterEl?.querySelector('[role="progressbar"]');
  const MAX_HIGHLIGHTS = 8;
  const MIN_HIGHLIGHTS = 3;

  function escapeHtml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function getHighlightInputs() {
    return Array.from(fieldsRoot?.querySelectorAll('[data-hl-input]') || []);
  }

  function getHighlightValues() {
    return getHighlightInputs().map((el) => el.value.trim()).filter(Boolean);
  }

  function renumberFields() {
    const fields = Array.from(fieldsRoot?.querySelectorAll('[data-hl-field]') || []);
    fields.forEach((field, index) => {
      const num = index + 1;
      const numEl = field.querySelector('.partner-vitrine-hl-field__num');
      const titleEl = field.querySelector('.partner-vitrine-hl-field__title');
      const input = field.querySelector('[data-hl-input]');
      const removeBtn = field.querySelector('[data-hl-remove]');
      if (numEl) numEl.textContent = String(num);
      if (titleEl) titleEl.textContent = `Atout ${num}`;
      if (input) {
        input.id = `profile-hl-${num}`;
        const label = field.querySelector('label');
        if (label) label.setAttribute('for', `profile-hl-${num}`);
      }
      if (removeBtn) removeBtn.hidden = num <= MIN_HIGHLIGHTS;
    });
    if (addBtn) addBtn.hidden = fields.length >= MAX_HIGHLIGHTS;
  }

  function createField(value = '') {
    const count = getHighlightInputs().length + 1;
    const field = document.createElement('div');
    field.className = 'partner-vitrine-hl-field';
    field.dataset.hlField = '';

    const label = document.createElement('label');
    label.className = 'partner-vitrine-hl-field__label';
    label.htmlFor = `profile-hl-${count}`;
    label.innerHTML = `<span class="partner-vitrine-hl-field__num" aria-hidden="true">${count}</span><span class="partner-vitrine-hl-field__title">Atout ${count}</span>`;

    const wrap = document.createElement('div');
    wrap.className = 'partner-vitrine-hl-field__wrap';

    const input = document.createElement('input');
    input.type = 'text';
    input.id = `profile-hl-${count}`;
    input.name = 'profile_highlights[]';
    input.className = 'partner-vitrine-hl-field__input';
    input.maxLength = 220;
    input.placeholder = 'Un atout concret pour vos voyageurs';
    input.dataset.hlInput = '';
    input.value = value;
    input.addEventListener('input', updateHighlights);

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'partner-vitrine-hl-field__remove';
    removeBtn.dataset.hlRemove = '';
    removeBtn.setAttribute('aria-label', 'Supprimer cet atout');
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => {
      if (getHighlightInputs().length <= MIN_HIGHLIGHTS) return;
      field.remove();
      renumberFields();
      updateHighlights();
    });

    wrap.append(input, removeBtn);
    field.append(label, wrap);
    return field;
  }

  function updateHighlights() {
    const lines = getHighlightValues();
    const count = lines.length;
    if (countEl) countEl.textContent = String(count);
    if (statusEl) {
      statusEl.textContent = `${count} point${count !== 1 ? 's' : ''}`;
      statusEl.classList.toggle('partner-vitrine-panel__status--ok', count >= MIN_HIGHLIGHTS);
    }
    if (fillEl) {
      const pct = Math.min(100, Math.round((count / MIN_HIGHLIGHTS) * 100));
      fillEl.style.width = `${pct}%`;
    }
    if (meterEl) meterEl.classList.toggle('is-complete', count >= MIN_HIGHLIGHTS);
    if (minHintEl) {
      minHintEl.textContent = count >= MIN_HIGHLIGHTS ? '✓ minimum atteint' : `· minimum ${MIN_HIGHLIGHTS} atouts`;
    }
    if (meterTrack) meterTrack.setAttribute('aria-valuenow', String(count));
    if (previewWrap && previewList) {
      previewWrap.hidden = count === 0;
      previewList.innerHTML = lines
        .slice(0, MAX_HIGHLIGHTS)
        .map(
          (line) =>
            `<li class="partner-vitrine-hl-preview__item"><span class="partner-vitrine-hl-preview__check" aria-hidden="true">✓</span><span>${escapeHtml(line)}</span></li>`,
        )
        .join('');
    }
  }

  getHighlightInputs().forEach((input) => input.addEventListener('input', updateHighlights));

  fieldsRoot?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-hl-remove]');
    if (!btn) return;
    const field = btn.closest('[data-hl-field]');
    if (!field || getHighlightInputs().length <= MIN_HIGHLIGHTS) return;
    field.remove();
    renumberFields();
    updateHighlights();
  });

  addBtn?.addEventListener('click', () => {
    if (getHighlightInputs().length >= MAX_HIGHLIGHTS) return;
    fieldsRoot?.appendChild(createField());
    renumberFields();
    fieldsRoot?.lastElementChild?.querySelector('[data-hl-input]')?.focus();
    updateHighlights();
  });

  renumberFields();
  updateHighlights();

  const fileInput = document.getElementById('partner-photo-file');
  const previewFrame = document.getElementById('partner-photo-preview');
  const filenameEl = document.getElementById('partner-photo-filename');
  const dropzone = document.getElementById('partner-photo-dropzone');
  const urlInput = document.getElementById('partner-photo-url');
  const clearCheckbox = document.getElementById('partner-photo-clear');

  function setPreviewImage(src, label) {
    if (!previewFrame) return;
    previewFrame.dataset.hasCustom = '1';
    previewFrame.innerHTML = `
      <img src="${src}" alt="Aperçu photo de couverture" width="640" height="360" id="partner-photo-preview-img">
      <span class="partner-vitrine-upload__badge">Aperçu</span>`;
    if (filenameEl && label) filenameEl.textContent = label;
    if (clearCheckbox) clearCheckbox.checked = false;
    dropzone?.classList.add('is-selected');
  }

  function resetPreviewLabel() {
    if (filenameEl) filenameEl.textContent = 'JPG, PNG ou WebP';
    dropzone?.classList.remove('is-selected');
  }

  fileInput?.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    if (!file) {
      resetPreviewLabel();
      return;
    }
    if (filenameEl) filenameEl.textContent = file.name;
    dropzone?.classList.add('is-selected');
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result) setPreviewImage(e.target.result, file.name);
    };
    reader.readAsDataURL(file);
  });

  urlInput?.addEventListener('change', () => {
    const raw = urlInput.value.trim();
    if (!raw) return;
    const url = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
    setPreviewImage(url, 'URL externe');
  });

  if (dropzone && fileInput) {
    ['dragenter', 'dragover'].forEach((ev) => {
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.add('is-dragover');
      });
    });
    ['dragleave', 'drop'].forEach((ev) => {
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.remove('is-dragover');
      });
    });
    dropzone.addEventListener('drop', (e) => {
      const file = e.dataTransfer?.files?.[0];
      if (!file || !file.type.startsWith('image/')) return;
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  const vitrineForm = fieldsRoot?.closest('form') || document.getElementById('partner-vitrine-form');
  vitrineForm?.addEventListener('submit', () => {
    if (urlInput) {
      const raw = urlInput.value.trim();
      if (raw && !/^https?:\/\//i.test(raw)) {
        urlInput.value = `https://${raw}`;
      }
    }
  });
});
