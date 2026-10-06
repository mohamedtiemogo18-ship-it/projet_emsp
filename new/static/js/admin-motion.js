/* Refonte étape 3 : compteurs animés du tableau de bord (valeurs lues dans le HTML rendu par Flask) */
(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('.admin-stat__value, .admin-storage__count').forEach((el, i) => {
    const target = parseInt(el.textContent, 10);
    if (!Number.isFinite(target) || target < 1) return;
    const start = performance.now() + 250 + i * 70;
    const tick = (now) => {
      const k = Math.max(0, Math.min(1, (now - start) / 1000));
      el.textContent = String(Math.round(target * (1 - Math.pow(1 - k, 3))));
      if (k < 1) requestAnimationFrame(tick);
    };
    el.textContent = '0';
    requestAnimationFrame(tick);
  });
})();
