(function () {
  const STATUS_CLASS = ['aff-verify--ok', 'aff-verify--warn', 'aff-verify--error'];

  function boxForInput(input) {
    const card = input.closest('.partner-card');
    return card ? card.querySelector('.aff-verify') : null;
  }

  function renderVerify(box, data) {
    if (!box) return;
    STATUS_CLASS.forEach((c) => box.classList.remove(c));
    box.classList.add(`aff-verify--${data.status || 'error'}`);
    const msg = box.querySelector('.aff-verify__msg');
    if (msg) msg.textContent = data.message || '';

    let sample = box.querySelector('.aff-verify__sample');
    if (data.sample_url && data.sample_url.startsWith('http')) {
      if (!sample) {
        sample = document.createElement('p');
        sample.className = 'aff-verify__sample';
        sample.innerHTML = '<span class="aff-verify__label">Lien exemple généré par le site :</span> ';
        box.appendChild(sample);
      }
      const href = data.sample_url;
      const short = href.length > 80 ? `${href.slice(0, 80)}…` : href;
      sample.innerHTML = `<span class="aff-verify__label">Lien exemple généré par le site :</span> <a href="${href}" target="_blank" rel="noopener" class="aff-verify__link">${short}</a>`;
    } else if (sample) {
      sample.remove();
    }
  }

  async function verifyInput(input) {
    const idKey = input.dataset.idKey;
    if (!idKey) return;
    const box = boxForInput(input);
    if (box) {
      box.classList.add('aff-verify--loading');
      const msg = box.querySelector('.aff-verify__msg');
      if (msg) msg.textContent = 'Vérification…';
    }
    try {
      const res = await fetch('/admin/api/affiliate-verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_key: idKey, value: input.value }),
      });
      const data = await res.json();
      if (box) {
        box.classList.remove('aff-verify--loading');
        renderVerify(box, data);
      }
      if (data.normalized && data.normalized !== input.value.trim() && data.status === 'ok') {
        input.value = data.normalized;
      }
    } catch {
      if (box) {
        box.classList.remove('aff-verify--loading');
        renderVerify(box, { status: 'error', message: 'Erreur réseau — réessayez.' });
      }
    }
  }

  let timer;
  document.querySelectorAll('.aff-id-input').forEach((input) => {
    input.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => verifyInput(input), 450);
    });
    input.addEventListener('blur', () => verifyInput(input));
  });
})();
