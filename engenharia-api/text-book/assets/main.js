/* ============================================================
   Do Notebook à Produção — Lógica compartilhada
   Cada página define window.TB_CHAPTERS antes de carregar este arquivo:
     [{ id:'01', path:'01-refatoracao-pipeline.html', title:'...' }, ...]
   ============================================================ */

// Tema Mermaid padronizado com o design system (usar em cada capítulo)
window.TB_MERMAID_THEME = {
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    primaryColor: '#EDE9FE', primaryTextColor: '#5B21B6', primaryBorderColor: '#7C3AED',
    lineColor: '#CEC9BF', secondaryColor: '#F0EDE6', tertiaryColor: '#FDFBF7',
    edgeLabelBackground: '#FDFBF7', fontFamily: "'DM Sans', sans-serif", fontSize: '14px',
    nodeBorder: '#E2DDD4', clusterBkg: '#F5F2EC', clusterBorder: '#E2DDD4', titleColor: '#1C1917',
  },
};

// ── App da homepage (index.html) ──
function indexApp() {
  const chapters = window.TB_CHAPTERS || [];
  return {
    sidebarCollapsed: false,
    visited: {},
    init() {
      this.sidebarCollapsed = localStorage.getItem('tb_sidebar_collapsed') === 'true';
      const v = {};
      chapters.forEach(c => { v[c.id] = localStorage.getItem('visited_' + c.path) === 'true'; });
      this.visited = v;
    },
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      localStorage.setItem('tb_sidebar_collapsed', this.sidebarCollapsed);
    },
    isVisited(id) { return !!this.visited[id]; },
    get visitedCount() { return Object.values(this.visited).filter(Boolean).length; },
    get totalChapters() { return chapters.length; },
    get progressPct() { return chapters.length ? Math.round((this.visitedCount / chapters.length) * 100) : 0; },
  };
}

// ── App dos capítulos ──
function chapterApp(currentId) {
  const chapters = window.TB_CHAPTERS || [];
  return {
    sidebarCollapsed: false,
    activeSection: '',
    currentChapter: currentId,
    init() {
      this.sidebarCollapsed = localStorage.getItem('tb_sidebar_collapsed') === 'true';
      localStorage.setItem('visited_' + location.pathname.split('/').pop(), 'true');
      // barra de progresso de leitura
      const onScroll = () => {
        const doc = document.documentElement;
        const pct = doc.scrollHeight > doc.clientHeight
          ? (doc.scrollTop / (doc.scrollHeight - doc.clientHeight)) * 100 : 0;
        const bar = document.getElementById('reading-progress');
        if (bar) bar.style.width = pct + '%';
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
      // active tracking das seções por scroll
      const sections = document.querySelectorAll('h2[id], h3[id]');
      if (sections.length) {
        const obs = new IntersectionObserver((entries) => {
          entries.forEach(e => { if (e.isIntersecting) this.activeSection = e.target.id; });
        }, { rootMargin: '-15% 0px -70% 0px' });
        sections.forEach(s => obs.observe(s));
      }
    },
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      localStorage.setItem('tb_sidebar_collapsed', this.sidebarCollapsed);
    },
    isVisited(id) {
      const c = (window.TB_CHAPTERS || []).find(x => x.id === id);
      return c ? localStorage.getItem('visited_' + c.path) === 'true' : false;
    },
  };
}

// ── Copiar código (botões .copy-btn) ──
function tbCopyCode(btn) {
  const wrap = btn.closest('.code-wrap');
  const code = wrap ? wrap.querySelector('code') : null;
  if (!code) return;
  navigator.clipboard.writeText(code.textContent.replace(/\n$/, '')).then(() => {
    const original = btn.textContent;
    btn.textContent = '✓ Copiado';
    setTimeout(() => { btn.textContent = original; }, 1800);
  });
}
window.tbCopyCode = tbCopyCode;

// ── Mermaid: clicar para ampliar (modal com zoom + pan) ──
function tbInitMermaidZoom() {
  const wraps = document.querySelectorAll('.mermaid-wrap');
  if (!wraps.length) return;

  // modal único
  let modal = document.getElementById('mm-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'mm-modal';
    modal.className = 'mm-modal';
    modal.innerHTML =
      '<div class="mm-dialog" role="dialog" aria-modal="true">' +
        '<div class="mm-bar">' +
          '<span class="mm-hint">Arraste para mover · role o mouse para dar zoom</span>' +
          '<div class="mm-tools">' +
            '<button class="mm-tool" data-act="out" title="Diminuir">−</button>' +
            '<button class="mm-tool" data-act="reset" title="Ajustar à tela">⤢</button>' +
            '<button class="mm-tool" data-act="in" title="Aumentar">+</button>' +
            '<button class="mm-tool" data-act="close" title="Fechar (Esc)" style="margin-left:0.4rem">✕</button>' +
          '</div>' +
        '</div>' +
        '<div class="mm-stage"><div class="mm-canvas"></div></div>' +
      '</div>';
    document.body.appendChild(modal);
  }

  const stage = modal.querySelector('.mm-stage');
  const canvas = modal.querySelector('.mm-canvas');
  let scale = 1, tx = 0, ty = 0, baseScale = 1;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const apply = () => { canvas.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')'; };

  function intrinsic(svg) {
    const vb = svg.getAttribute('viewBox');
    if (vb) { const p = vb.split(/[\s,]+/).map(Number); if (p.length === 4 && p[2] && p[3]) return { w: p[2], h: p[3] }; }
    try { const b = svg.getBBox(); return { w: b.width || 600, h: b.height || 400 }; }
    catch (e) { return { w: 600, h: 400 }; }
  }
  function fit() {
    const svg = canvas.querySelector('svg');
    if (!svg) return;
    const s = stage.getBoundingClientRect();
    const dim = intrinsic(svg);
    canvas.style.width = dim.w + 'px';
    canvas.style.height = dim.h + 'px';
    svg.setAttribute('width', dim.w);
    svg.setAttribute('height', dim.h);
    baseScale = clamp(Math.min(s.width / dim.w, s.height / dim.h) * 0.94, 0.05, 4);
    scale = baseScale;
    tx = (s.width - dim.w * scale) / 2;
    ty = (s.height - dim.h * scale) / 2;
    apply();
  }
  function zoomAround(cx, cy, factor) {
    const ns = clamp(scale * factor, baseScale * 0.4, baseScale * 14);
    tx = cx - (cx - tx) * (ns / scale);
    ty = cy - (cy - ty) * (ns / scale);
    scale = ns; apply();
  }
  function openModal(wrap) {
    const svg = wrap.querySelector('svg');
    if (!svg) return;
    canvas.innerHTML = '';
    const clone = svg.cloneNode(true);
    clone.removeAttribute('style');
    canvas.appendChild(clone);
    modal.classList.add('open');
    requestAnimationFrame(fit);
  }
  function closeModal() { modal.classList.remove('open'); canvas.innerHTML = ''; }

  // botão "Ampliar" + clique no diagrama
  wraps.forEach((w) => {
    w.style.cursor = 'zoom-in';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'mm-zoom-btn';
    btn.innerHTML = '⤢ Ampliar';
    btn.addEventListener('click', (e) => { e.stopPropagation(); openModal(w); });
    w.appendChild(btn);
    w.addEventListener('click', (e) => {
      if (e.target.closest('.mm-zoom-btn')) return;
      if (w.querySelector('svg')) openModal(w);
    });
  });

  // controles do modal
  modal.querySelector('.mm-tools').addEventListener('click', (e) => {
    const act = e.target.closest('.mm-tool')?.dataset.act;
    if (!act) return;
    const r = stage.getBoundingClientRect();
    if (act === 'in') zoomAround(r.width / 2, r.height / 2, 1.25);
    else if (act === 'out') zoomAround(r.width / 2, r.height / 2, 1 / 1.25);
    else if (act === 'reset') fit();
    else if (act === 'close') closeModal();
  });
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

  // zoom com a roda do mouse (centrado no cursor)
  stage.addEventListener('wheel', (e) => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoomAround(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, { passive: false });

  // pan com arraste
  let dragging = false, sx = 0, sy = 0;
  stage.addEventListener('pointerdown', (e) => {
    dragging = true; sx = e.clientX - tx; sy = e.clientY - ty;
    stage.classList.add('grabbing'); stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener('pointermove', (e) => {
    if (!dragging) return; tx = e.clientX - sx; ty = e.clientY - sy; apply();
  });
  const endDrag = () => { dragging = false; stage.classList.remove('grabbing'); };
  stage.addEventListener('pointerup', endDrag);
  stage.addEventListener('pointercancel', endDrag);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', tbInitMermaidZoom);
} else {
  tbInitMermaidZoom();
}
