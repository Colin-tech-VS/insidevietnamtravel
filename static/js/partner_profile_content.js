document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('partner-content-blocks');
  if (!root) return;

  function nextGalleryIndex(blockId) {
    const rows = root.querySelectorAll(`[data-content-rows="${blockId}"] [data-gallery-index]`);
    let max = -1;
    rows.forEach((row) => {
      const n = parseInt(row.getAttribute('data-gallery-index') || '0', 10);
      if (n > max) max = n;
    });
    return max + 1;
  }

  function bindRemove(btn) {
    btn.addEventListener('click', () => {
      const row = btn.closest('[data-content-row]');
      const container = row?.parentElement;
      if (!row || !container) return;
      if (container.querySelectorAll('[data-content-row]').length <= 1) {
        row.querySelectorAll('input:not([type="file"])').forEach((el) => {
          if (el.type !== 'hidden' || el.name.includes('_existing')) el.value = '';
        });
        const preview = row.querySelector('.partner-gallery-row__preview');
        if (preview) preview.innerHTML = '<span class="partner-gallery-row__empty">Aucune image</span>';
        return;
      }
      row.remove();
    });
  }

  root.querySelectorAll('[data-content-remove]').forEach(bindRemove);

  root.querySelectorAll('[data-content-add]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const blockId = btn.getAttribute('data-content-add');
      const blockType = btn.getAttribute('data-content-type') || '';
      const container = root.querySelector(`[data-content-rows="${blockId}"]`);
      const block = btn.closest('[data-content-block]');
      const max = parseInt(block?.getAttribute('data-block-max') || '8', 10);
      if (!container || container.querySelectorAll('[data-content-row]').length >= max) return;

      if (blockType === 'gallery') {
        const idx = nextGalleryIndex(blockId);
        const row = document.createElement('div');
        row.className = 'partner-gallery-row';
        row.dataset.contentRow = '';
        row.dataset.galleryIndex = String(idx);
        row.innerHTML = `
          <div class="partner-gallery-row__preview"><span class="partner-gallery-row__empty">Aucune image</span></div>
          <div class="partner-gallery-row__fields">
            <input type="hidden" name="pc_${blockId}_existing[]" value="">
            <input type="text" name="pc_${blockId}_caption[]" class="partner-content-row__input" maxlength="160" placeholder="Légende (optionnel)">
            <label class="partner-gallery-row__file">
              <span class="btn btn-ghost btn-sm">Choisir une photo</span>
              <input type="file" name="pc_${blockId}_file_${idx}" accept="image/jpeg,image/png,image/webp,image/gif" class="partner-gallery-row__input-file">
            </label>
          </div>
          <button type="button" class="partner-content-row__remove" data-content-remove aria-label="Supprimer">×</button>`;
        container.appendChild(row);
        bindRemove(row.querySelector('[data-content-remove]'));
        bindGalleryPreview(row);
        return;
      }

      const first = container.querySelector('[data-content-row]');
      if (!first) return;
      const clone = first.cloneNode(true);
      clone.querySelectorAll('input').forEach((el) => {
        el.value = '';
      });
      container.appendChild(clone);
      bindRemove(clone.querySelector('[data-content-remove]'));
    });
  });

  function bindGalleryPreview(row) {
    const fileInput = row.querySelector('.partner-gallery-row__input-file');
    const preview = row.querySelector('.partner-gallery-row__preview');
    if (!fileInput || !preview) return;
    fileInput.addEventListener('change', () => {
      const file = fileInput.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result) {
          preview.innerHTML = `<img src="${e.target.result}" alt="" width="120" height="80" loading="lazy">`;
        }
      };
      reader.readAsDataURL(file);
      const existing = row.querySelector('input[name$="_existing[]"]');
      if (existing) existing.value = '';
    });
  }

  root.querySelectorAll('.partner-gallery-row').forEach(bindGalleryPreview);
});
