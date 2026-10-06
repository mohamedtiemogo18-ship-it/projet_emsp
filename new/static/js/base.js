(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('[data-theme-toggle]');
  const navButton = document.querySelector('[data-nav-toggle]');
  const nav = navButton ? document.getElementById(navButton.getAttribute('aria-controls')) : null;
  const themeStorageKey = 'emsp-theme';
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  const readSavedTheme = () => {
    try {
      return window.localStorage.getItem(themeStorageKey);
    } catch (_error) {
      return null;
    }
  };

  const applyTheme = (theme) => {
    const isDark = theme === 'dark';
    root.dataset.theme = isDark ? 'dark' : 'light';
    root.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
    if (themeButton) {
      themeButton.setAttribute('aria-pressed', String(isDark));
      themeButton.setAttribute('aria-label', isDark ? 'Activer le thème clair' : 'Activer le thème sombre');
      themeButton.innerHTML = `<i class="bi ${isDark ? 'bi-sun-fill' : 'bi-moon-stars-fill'}" aria-hidden="true"></i>`;
    }
  };

  applyTheme(readSavedTheme() || (prefersDark ? 'dark' : 'light'));

  themeButton?.addEventListener('click', () => {
    const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(theme);
    try {
      window.localStorage.setItem(themeStorageKey, theme);
    } catch (_error) {
      // Theme remains active for the current page when storage is unavailable.
    }
  });

  navButton?.addEventListener('click', () => {
    const isOpen = navButton.getAttribute('aria-expanded') === 'true';
    const nextLabel = isOpen ? 'Ouvrir le menu' : 'Fermer le menu';
    navButton.setAttribute('aria-expanded', String(!isOpen));
    navButton.setAttribute('aria-label', nextLabel);
    const icon = navButton.querySelector('i');
    icon?.classList.toggle('bi-list', isOpen);
    icon?.classList.toggle('bi-x-lg', !isOpen);
    const screenReaderLabel = navButton.querySelector('.sr-only');
    if (screenReaderLabel) screenReaderLabel.textContent = nextLabel;
    nav?.classList.toggle('is-open', !isOpen);
  });

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (window.gsap && !reduceMotion) {
    const intro = document.querySelector('.public-hero h1, .admin-content__header h1, .page-heading h1');
    if (intro) window.gsap.from(intro, { autoAlpha: 0, y: 8, duration: 0.38, ease: 'power2.out', immediateRender: false });
  }
})();