/* Refonte étape 2 : anneau de progression et repère glissant, branchés sur la logique existante de script.js */
(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const C = 2 * Math.PI * 34;
  const bar = document.getElementById('completionBar');
  const fg = document.getElementById('sideRingFg');
  const pct = document.getElementById('sideRingPct');
  const lbl = document.getElementById('sideRingLbl');
  let shown = 0;

  const setRing = (value) => {
    if (!fg) return;
    fg.style.strokeDashoffset = String(C * (1 - value / 100));
    if (lbl) lbl.textContent = value >= 100 ? 'Dossier complet' : value === 0 ? 'À compléter' : 'En cours';
    const from = shown, start = performance.now();
    const tick = (now) => {
      const k = reduce ? 1 : Math.min(1, (now - start) / 900);
      pct.textContent = Math.round(from + (value - from) * (1 - Math.pow(1 - k, 3))) + '%';
      if (k < 1) requestAnimationFrame(tick); else shown = value;
    };
    requestAnimationFrame(tick);
  };

  if (bar && fg) {
    fg.style.strokeDasharray = String(C);
    fg.style.strokeDashoffset = String(C);
    const read = () => Number(bar.getAttribute('aria-valuenow')) || 0;
    new MutationObserver(() => setRing(read())).observe(bar, { attributes: true, attributeFilter: ['aria-valuenow'] });
    setRing(read());
  }


  /* Étapes cochées : une section est terminée quand tous ses champs obligatoires sont remplis */
  const form = document.getElementById("inscriptionForm");
  const filled = (f) => f.type === "checkbox" ? f.checked : f.type === "file" ? !!(f.files && f.files.length) : f.value.trim() !== "";
  const refreshDone = () => {
    document.querySelectorAll(".candidate-stepper .step[data-section]").forEach((link) => {
      const sec = document.getElementById(link.dataset.section);
      const req = sec ? [...sec.querySelectorAll("input[required], select[required], textarea[required]")] : [];
      const ok = req.length > 0 && req.every(filled);
      link.classList.toggle("step--done", ok);
      link.classList.toggle("step--upcoming", !ok && !link.classList.contains("step--current"));
    });
  };

  /* Indicateur d'enregistrement : reflète l'état réel du brouillon, sans sauvegarde automatique */
  const state = document.getElementById('saveState');
  const setState = (kind, text) => {
    if (!state) return;
    state.dataset.state = kind;
    state.querySelector('span').textContent = text;
    state.classList.remove('pulse'); void state.offsetWidth;
    if (kind === 'saved') state.classList.add('pulse');
  };
  if (form) {
    const onEdit = () => { refreshDone(); setState('dirty', 'Modifications non enregistrées'); };
    form.addEventListener('input', onEdit);
    form.addEventListener('change', onEdit);
    ['validateGeneral', 'validateBac', 'validateTuteurs', 'validateDocuments'].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      new MutationObserver(() => { if (/enregistré/i.test(btn.textContent)) setState('saved', 'Brouillon enregistré'); }).observe(btn, { childList: true, characterData: true, subtree: true });
    });
    refreshDone();
  }

  const menu = document.querySelector('.sidebar-menu');
  if (!menu) return;
})();
