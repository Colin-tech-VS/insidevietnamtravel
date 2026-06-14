document.addEventListener('DOMContentLoaded', () => {
  const textarea = document.getElementById('profile_highlights');
  const countEl = document.getElementById('vitrine-hl-count');
  const fillEl = document.getElementById('vitrine-hl-fill');
  const meterEl = document.getElementById('vitrine-hl-meter');
  const minHintEl = document.getElementById('vitrine-hl-min-hint');
  const statusEl = document.getElementById('vitrine-hl-status');
  const previewWrap = document.getElementById('vitrine-hl-preview');
  const previewList = document.getElementById('vitrine-hl-preview-list');
  const meterTrack = meterEl?.querySelector('[role="progressbar"]');

  function parseHighlights(value) {
    return value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  }

  function updateHighlights() {
    if (!textarea || !countEl) return;
    const lines = parseHighlights(textarea.value);
    const count = lines.length;
    countEl.textContent = String(count);
    if (statusEl) {
      statusEl.textContent = `${count} point${count !== 1 ? 's' : ''}`;
      statusEl.classList.toggle('partner-vitrine-panel__status--ok', count >= 3);
    }
    if (fillEl) {
      const pct = Math.min(100, Math.round((count / 3) * 100));
      fillEl.style.width = `${pct}%`;
    }
    if (meterEl) {
      meterEl.classList.toggle('is-complete', count >= 3);
    }
    if (minHintEl) {
      minHintEl.textContent = count >= 3 ? '✓ minimum atteint' : '· minimum 3 lignes';
    }
    if (meterTrack) {
      meterTrack.setAttribute('aria-valuenow', String(count));
    }
    if (previewWrap && previewList) {
      previewWrap.hidden = count === 0;
      previewList.innerHTML = lines
        .slice(0, 8)
        .map(
          (line) =>
            `<li class="partner-vitrine-hl-preview__item"><span class="partner-vitrine-hl-preview__check" aria-hidden="true">✓</span><span>${escapeHtml(line)}</span></li>`,
        )
        .join('');
    }
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  textarea?.addEventListener('input', updateHighlights);
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

  const vitrineForm = textarea?.closest('form') || document.getElementById('partner-vitrine-form');
  vitrineForm?.addEventListener('submit', () => {
    if (!urlInput) return;
    const raw = urlInput.value.trim();
    if (raw && !/^https?:\/\//i.test(raw)) {
      urlInput.value = `https://${raw}`;
    }
  });
});
