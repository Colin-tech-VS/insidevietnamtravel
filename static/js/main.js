// Maillage interne : les liens internes portent des paramètres UTM pour l'analytics.
// Ils sont comptabilisés côté serveur dès le chargement (log au GET) puis, si présent,
// par GA4. On les retire ensuite discrètement de la barre d'adresse pour qu'ils restent
// INVISIBLES à l'utilisateur, sans perdre le suivi. Le délai laisse à GA4 (chargé après
// consentement) le temps de lire l'URL d'origine.
(function stripTrackingParams() {
  try {
    const url = new URL(window.location.href);
    const utmKeys = Array.from(url.searchParams.keys()).filter(
      (k) => k.toLowerCase().indexOf('utm_') === 0,
    );
    if (!utmKeys.length || !window.history || !window.history.replaceState) return;
    window.setTimeout(() => {
      utmKeys.forEach((k) => url.searchParams.delete(k));
      const qs = url.searchParams.toString();
      window.history.replaceState(
        window.history.state,
        document.title,
        url.pathname + (qs ? '?' + qs : '') + url.hash,
      );
    }, 1200);
  } catch (e) {
    /* no-op */
  }
})();

document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');
  const backdrop = document.getElementById('nav-backdrop');
  const dropdowns = document.querySelectorAll('.nav-dropdown');
  const MOBILE_NAV_MQ = window.matchMedia('(max-width: 1024px)');

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
        if (MOBILE_NAV_MQ.matches) {
          setNavOpen(false);
        } else {
          closeDropdowns();
        }
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
