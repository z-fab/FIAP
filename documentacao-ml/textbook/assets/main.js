/* ===================================================================
   Textbook — helpers compartilhados
   =================================================================== */

// Lista ordenada de capítulos — usada por sidebar, nav e persistência
window.TB_CHAPTERS = [
  { id: '01', file: '01-importancia-documentacao.html',   title: 'Por que documentação importa' },
  { id: '02', file: '02-model-cards.html',                 title: 'Model Cards' },
  { id: '03', file: '03-readme-mermaid.html',              title: 'README + Mermaid' },
  { id: '04', file: '04-docstrings-type-hints.html',       title: 'Docstrings, type hints e IA' },
  { id: '05', file: '05-mlflow-star.html',                 title: 'MLflow + método STAR' },
  { id: '06', file: '06-checklist-tech-challenge.html',    title: 'Checklist Tech Challenge' },
];

// ------------------------- Sidebar collapse -------------------------
// Se Alpine não for usado numa página, este helper garante o comportamento.
window.TB_initSidebarFallback = function () {
  const sb = document.querySelector('.sb');
  if (!sb) return;
  const collapsed = localStorage.getItem('tb_sidebar_collapsed') === 'true';
  if (collapsed) sb.classList.add('col');
  const main = document.querySelector('.main');
  if (main && collapsed) main.classList.add('col');
};

// ------------------------- Code copy buttons -------------------------
window.TB_addCopyButtons = function () {
  document.querySelectorAll('.content pre').forEach(pre => {
    if (pre.querySelector('.code-copy')) return;
    const btn = document.createElement('button');
    btn.className = 'code-copy';
    btn.type = 'button';
    btn.textContent = 'Copiar';
    btn.addEventListener('click', () => {
      const code = pre.querySelector('code') || pre;
      const text = code.textContent || '';
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '✓ Copiado';
        setTimeout(() => (btn.textContent = 'Copiar'), 1800);
      }).catch(() => {
        btn.textContent = 'Falhou';
        setTimeout(() => (btn.textContent = 'Copiar'), 1800);
      });
    });
    pre.appendChild(btn);
  });
};

// ------------------------- Active section tracking (IntersectionObserver) -------------------------
window.TB_initSectionObserver = function (onActive) {
  const sections = document.querySelectorAll('.content h2[id], .content h3[id]');
  if (!sections.length || typeof onActive !== 'function') return;
  const obs = new IntersectionObserver(
    entries => { entries.forEach(e => { if (e.isIntersecting) onActive(e.target.id); }); },
    { rootMargin: '-12% 0px -70% 0px' }
  );
  sections.forEach(s => obs.observe(s));
};

// ------------------------- Reading progress bar -------------------------
window.TB_initReadingProgress = function () {
  const bar = document.getElementById('reading-progress');
  if (!bar) return;
  const update = () => {
    const doc = document.documentElement;
    const total = doc.scrollHeight - doc.clientHeight;
    const pct = total > 0 ? (doc.scrollTop / total) * 100 : 0;
    bar.style.width = pct + '%';
  };
  window.addEventListener('scroll', update, { passive: true });
  update();
};

// ------------------------- Visited marker -------------------------
window.TB_markVisited = function () {
  const file = location.pathname.split('/').pop();
  if (file && file.endsWith('.html') && file !== 'index.html') {
    localStorage.setItem('visited_' + file, 'true');
  }
};

// ------------------------- Chapter helpers -------------------------
window.TB_isVisited = function (id) {
  const ch = window.TB_CHAPTERS.find(c => c.id === id);
  if (!ch) return false;
  return localStorage.getItem('visited_' + ch.file) === 'true';
};
