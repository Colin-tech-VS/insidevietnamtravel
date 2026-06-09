(function initAdminLoaders() {
  'use strict';

  const STORAGE_KEY = 'adminLoader';
  const pageLoader = document.getElementById('page-loader');
  const actionLoader = document.getElementById('admin-action-loader');
  const actionText = document.getElementById('admin-action-loader-text');

  const NAV_MIN_MS = 320;
  const ACTION_FADE_MS = 180;
  const loadStarted = performance.now();
  let pageHideScheduled = false;

  function setPageLoaderVisible(visible) {
    if (!pageLoader) return;
    document.body.classList.toggle('is-loading', visible);
    pageLoader.classList.toggle('is-hidden', !visible);
    pageLoader.setAttribute('aria-busy', visible ? 'true' : 'false');
  }

  function hidePageLoader(minVisibleMs) {
    if (!pageLoader || pageHideScheduled) return;
    pageHideScheduled = true;
    const elapsed = performance.now() - loadStarted;
    const wait = Math.max(0, (minVisibleMs || 0) - elapsed);
    window.setTimeout(() => setPageLoaderVisible(false), wait);
  }

  function showPageLoader() {
    pageHideScheduled = false;
    setPageLoaderVisible(true);
  }

  function showActionLoader(label) {
    if (!actionLoader) return;
    if (actionText) actionText.textContent = label || 'Traitement en cours…';
    actionLoader.hidden = false;
    actionLoader.classList.add('is-visible');
    actionLoader.setAttribute('aria-hidden', 'false');
    actionLoader.setAttribute('aria-busy', 'true');
  }

  function hideActionLoader(delayMs) {
    if (!actionLoader) return;
    window.setTimeout(() => {
      actionLoader.classList.remove('is-visible');
      actionLoader.setAttribute('aria-hidden', 'true');
      actionLoader.setAttribute('aria-busy', 'false');
      window.setTimeout(() => {
        if (!actionLoader.classList.contains('is-visible')) actionLoader.hidden = true;
      }, ACTION_FADE_MS);
    }, delayMs || 0);
  }

  function actionLabel(form, submitter) {
    if (submitter?.dataset?.loaderText) return submitter.dataset.loaderText;
    const raw = (submitter?.value || submitter?.textContent || '').replace(/\s+/g, ' ').trim();
    if (raw) return raw.slice(0, 72);
    if (form?.dataset?.loaderText) return form.dataset.loaderText;
    return 'Traitement en cours…';
  }

  function shouldShowPageLoaderForLink(anchor) {
    if (!anchor || anchor.hasAttribute('download')) return false;
    const href = anchor.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return false;
    if (anchor.target === '_blank' || anchor.rel?.includes('external')) return false;
    if (anchor.dataset.noLoader !== undefined) return false;
    try {
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return false;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return false;
    } catch {
      return false;
    }
    return true;
  }

  // ── Fin de chargement : nav = loader page, action = barre rapide, sinon discret ──
  const loadMode = sessionStorage.getItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);

  if (loadMode === 'action') {
    setPageLoaderVisible(false);
    document.documentElement.classList.remove('admin-skip-page-loader');
    showActionLoader('Terminé');
    hideActionLoader(420);
  } else if (loadMode === 'nav') {
    if (document.readyState === 'complete') {
      hidePageLoader(NAV_MIN_MS);
    } else {
      document.addEventListener('DOMContentLoaded', () => hidePageLoader(NAV_MIN_MS), { once: true });
      window.addEventListener('load', () => hidePageLoader(NAV_MIN_MS), { once: true });
      window.setTimeout(() => hidePageLoader(0), 3500);
    }
  } else {
    hidePageLoader(0);
  }

  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      pageHideScheduled = false;
      hidePageLoader(0);
      hideActionLoader(0);
    }
  });

  document.addEventListener('click', (event) => {
    const anchor = event.target.closest('a[href]');
    if (!shouldShowPageLoaderForLink(anchor)) return;
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    try {
      const url = new URL(anchor.href, window.location.href);
      if (url.pathname === window.location.pathname) {
        sessionStorage.setItem(STORAGE_KEY, 'action');
        showActionLoader(anchor.dataset.loaderText || 'Chargement…');
        return;
      }
    } catch {
      return;
    }
    sessionStorage.setItem(STORAGE_KEY, 'nav');
    showPageLoader();
  });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.target === '_blank' || form.dataset.noLoader !== undefined) return;
    if (form.dataset.pageLoader !== undefined) {
      sessionStorage.setItem(STORAGE_KEY, 'nav');
      showPageLoader();
      return;
    }
    sessionStorage.setItem(STORAGE_KEY, 'action');
    showActionLoader(actionLabel(form, event.submitter));
  });
})();
