document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('partner-review');
  if (!root) return;
  const statusUrl = root.dataset.statusUrl;
  const dashboardUrl = root.dataset.dashboardUrl;
  const phaseEl = document.getElementById('partner-review-phase');
  if (!statusUrl) return;

  async function poll() {
    try {
      const res = await fetch(statusUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
      const st = await res.json();
      if (phaseEl && st.phase) phaseEl.textContent = st.phase;
      if (st.status === 'done' || st.status === 'error') {
        window.location.reload();
        return;
      }
    } catch (e) { /* retry */ }
    setTimeout(poll, 2500);
  }
  poll();
});
