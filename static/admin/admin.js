document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('admin-sidebar');
  const toggle = document.querySelector('.admin-sidebar-toggle');
  const backdrop = document.getElementById('admin-backdrop');
  const MOBILE_ADMIN_MQ = window.matchMedia('(max-width: 900px)');

  const setSidebarOpen = (isOpen) => {
    if (!sidebar || !toggle) return;
    sidebar.classList.toggle('is-open', isOpen);
    toggle.classList.toggle('is-active', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
    toggle.setAttribute('aria-label', isOpen ? 'Fermer le menu admin' : 'Ouvrir le menu admin');
    document.body.classList.toggle('is-admin-nav-open', isOpen);
    if (backdrop) {
      backdrop.classList.toggle('is-visible', isOpen);
      backdrop.setAttribute('aria-hidden', String(!isOpen));
    }
  };

  if (sidebar && toggle) {
    toggle.addEventListener('click', () => {
      setSidebarOpen(!sidebar.classList.contains('is-open'));
    });

    backdrop?.addEventListener('click', () => setSidebarOpen(false));

    sidebar.querySelectorAll('.admin-nav__link').forEach((link) => {
      link.addEventListener('click', () => {
        if (MOBILE_ADMIN_MQ.matches) setSidebarOpen(false);
      });
    });

    MOBILE_ADMIN_MQ.addEventListener('change', (e) => {
      if (!e.matches) setSidebarOpen(false);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
        setSidebarOpen(false);
      }
    });
  }
});
