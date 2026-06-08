(function initCookieConsent() {
  const STORAGE_KEY = 'ivt_cookie_consent';
  const MAX_AGE_MS = 13 * 30 * 24 * 60 * 60 * 1000;

  const banner = document.getElementById('cookie-banner');
  const settingsPanel = document.getElementById('cookie-settings');
  const analyticsToggle = document.getElementById('cookie-analytics-toggle');
  if (!banner) return;

  const readConsent = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data.ts || Date.now() - data.ts > MAX_AGE_MS) return null;
      return data;
    } catch {
      return null;
    }
  };

  const writeConsent = (analytics) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      essential: true,
      analytics: !!analytics,
      ts: Date.now(),
    }));
  };

  const loadAnalytics = () => {
    const ga4Id = document.body.dataset.ga4Id;
    if (!ga4Id) return;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() { window.dataLayer.push(arguments); };
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${ga4Id}`;
    script.onload = () => {
      window.gtag('js', new Date());
      window.gtag('config', ga4Id, { anonymize_ip: true });
    };
    document.head.appendChild(script);
  };

  const applyConsent = (consent) => {
    if (consent && consent.analytics) loadAnalytics();
    banner.hidden = true;
    if (settingsPanel) settingsPanel.hidden = true;
  };

  const showBanner = () => {
    banner.hidden = false;
  };

  const openSettings = () => {
    const consent = readConsent();
    if (analyticsToggle) {
      analyticsToggle.checked = consent ? !!consent.analytics : false;
    }
    if (settingsPanel) settingsPanel.hidden = false;
    banner.hidden = true;
  };

  document.querySelectorAll('[data-cookie-accept]').forEach((btn) => {
    btn.addEventListener('click', () => {
      writeConsent(true);
      applyConsent({ analytics: true });
    });
  });

  document.querySelectorAll('[data-cookie-reject]').forEach((btn) => {
    btn.addEventListener('click', () => {
      writeConsent(false);
      applyConsent({ analytics: false });
    });
  });

  document.querySelectorAll('[data-cookie-settings]').forEach((btn) => {
    btn.addEventListener('click', openSettings);
  });

  document.querySelectorAll('[data-cookie-save]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const analytics = analyticsToggle ? analyticsToggle.checked : false;
      writeConsent(analytics);
      applyConsent({ analytics });
    });
  });

  document.querySelectorAll('[data-cookie-settings-close]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (settingsPanel) settingsPanel.hidden = true;
      if (!readConsent()) showBanner();
    });
  });

  const existing = readConsent();
  if (existing) {
    applyConsent(existing);
  } else {
    showBanner();
  }
})();
