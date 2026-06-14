document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('partner-review');
  if (!root) return;
  const stateUrl = root.dataset.stateUrl;
  const phaseEl = document.getElementById('partner-review-phase');
  if (!stateUrl) return;

  let polls = 0;
  const maxPolls = 80; // ~3 min

  async function poll() {
    polls += 1;
    try {
      const res = await fetch(stateUrl, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      const data = await res.json();
      const job = data.job || {};
      if (phaseEl && job.phase) phaseEl.textContent = job.phase;

      if (data.page_ready || job.status === 'done' || job.status === 'error') {
        window.location.reload();
        return;
      }
      if (polls >= maxPolls) {
        window.location.reload();
        return;
      }
    } catch (e) {
      /* retry */
    }
    setTimeout(poll, 2500);
  }

  poll();
});
