document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');
  const dropdowns = document.querySelectorAll('.nav-dropdown');

  const closeDropdowns = (except) => {
    dropdowns.forEach((dd) => {
      if (dd !== except) {
        dd.classList.remove('is-open');
        const btn = dd.querySelector('.nav-dropdown__toggle');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      }
    });
  };

  dropdowns.forEach((dropdown) => {
    const btn = dropdown.querySelector('.nav-dropdown__toggle');
    if (!btn) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const willOpen = !dropdown.classList.contains('is-open');
      closeDropdowns(willOpen ? dropdown : null);
      dropdown.classList.toggle('is-open', willOpen);
      btn.setAttribute('aria-expanded', willOpen);
    });
  });

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', isOpen);
      toggle.setAttribute('aria-label', isOpen ? 'Fermer le menu' : 'Ouvrir le menu');
      if (!isOpen) closeDropdowns();
    });

    document.addEventListener('click', (e) => {
      if (!nav.contains(e.target) && !toggle.contains(e.target)) {
        if (nav.classList.contains('is-open')) {
          nav.classList.remove('is-open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.setAttribute('aria-label', 'Ouvrir le menu');
        }
        closeDropdowns();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDropdowns();
  });

  document.querySelectorAll('.flash').forEach((el) => {
    setTimeout(() => {
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 300);
    }, 4000);
  });
});
