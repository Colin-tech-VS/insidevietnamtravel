(function initPageLoader() {
  const loader = document.getElementById('page-loader');
  if (!loader) return;

  const MIN_VISIBLE_MS = 80;
  const MAX_VISIBLE_MS = 3500;
  const loadStarted = performance.now();
  let hideScheduled = false;

  const showLoader = () => {
    hideScheduled = false;
    document.body.classList.add('is-loading');
    loader.classList.remove('is-hidden');
    loader.setAttribute('aria-busy', 'true');
  };

  const hideLoader = () => {
    if (hideScheduled) return;
    hideScheduled = true;
    const elapsed = performance.now() - loadStarted;
    const wait = Math.max(0, MIN_VISIBLE_MS - elapsed);
    window.setTimeout(() => {
      loader.classList.add('is-hidden');
      document.body.classList.remove('is-loading');
      loader.setAttribute('aria-busy', 'false');
    }, wait);
  };

  const shouldShowForLink = (anchor) => {
    if (!anchor || anchor.hasAttribute('download')) return false;
    const href = anchor.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
      return false;
    }
    if (anchor.target === '_blank' || anchor.rel?.includes('external')) return false;
    if (anchor.dataset.noLoader !== undefined) return false;
    try {
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return false;
      if (url.pathname === window.location.pathname && url.search === window.location.search) {
        return false;
      }
    } catch {
      return false;
    }
    return true;
  };

  if (document.readyState === 'complete') {
    hideLoader();
  } else {
    document.addEventListener('DOMContentLoaded', hideLoader, { once: true });
    window.addEventListener('load', hideLoader, { once: true });
    window.setTimeout(hideLoader, MAX_VISIBLE_MS);
  }

  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      hideScheduled = false;
      hideLoader();
    }
  });

  document.addEventListener('click', (event) => {
    const anchor = event.target.closest('a[href]');
    if (!shouldShowForLink(anchor)) return;
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    showLoader();
  });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.target === '_blank' || form.dataset.noLoader !== undefined) return;
    showLoader();
  });
})();
