document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');
  const backdrop = document.getElementById('nav-backdrop');
  const dropdowns = document.querySelectorAll('.nav-dropdown');
  const MOBILE_NAV_MQ = window.matchMedia('(max-width: 768px)');

  const closeDropdowns = (except) => {
    dropdowns.forEach((dd) => {
      if (dd !== except) {
        dd.classList.remove('is-open');
        const btn = dd.querySelector('.nav-dropdown__toggle');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      }
    });
  };

  const setNavOpen = (isOpen) => {
    if (!nav || !toggle) return;
    nav.classList.toggle('is-open', isOpen);
    toggle.classList.toggle('is-active', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
    document.body.classList.toggle('is-nav-open', isOpen);
    if (backdrop) {
      backdrop.classList.toggle('is-visible', isOpen);
      backdrop.setAttribute('aria-hidden', String(!isOpen));
    }
    const openLabel = toggle.dataset.labelOpen || 'Open menu';
    const closeLabel = toggle.dataset.labelClose || 'Close menu';
    toggle.setAttribute('aria-label', isOpen ? closeLabel : openLabel);
    if (!isOpen) closeDropdowns();
  };

  dropdowns.forEach((dropdown) => {
    const btn = dropdown.querySelector('.nav-dropdown__toggle');
    if (!btn) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const willOpen = !dropdown.classList.contains('is-open');
      closeDropdowns(willOpen ? dropdown : null);
      dropdown.classList.toggle('is-open', willOpen);
      btn.setAttribute('aria-expanded', String(willOpen));
    });
  });

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      setNavOpen(!nav.classList.contains('is-open'));
    });

    backdrop?.addEventListener('click', () => setNavOpen(false));

    nav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        if (MOBILE_NAV_MQ.matches) setNavOpen(false);
      });
    });

    document.addEventListener('click', (e) => {
      if (!MOBILE_NAV_MQ.matches) {
        if (!nav.contains(e.target)) closeDropdowns();
        return;
      }
      if (!nav.contains(e.target) && !toggle.contains(e.target)) {
        setNavOpen(false);
      }
    });

    MOBILE_NAV_MQ.addEventListener('change', (e) => {
      if (!e.matches) setNavOpen(false);
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    closeDropdowns();
    if (nav?.classList.contains('is-open')) setNavOpen(false);
  });

  document.querySelectorAll('.flash').forEach((el) => {
    setTimeout(() => {
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 300);
    }, 4000);
  });
});
