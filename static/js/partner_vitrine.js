document.addEventListener('DOMContentLoaded', () => {
  const textarea = document.getElementById('profile_highlights');
  const countEl = document.getElementById('vitrine-hl-count');
  if (!textarea || !countEl) return;

  function updateCount() {
    const lines = textarea.value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    countEl.textContent = String(lines.length);
  }

  textarea.addEventListener('input', updateCount);
  updateCount();
});
