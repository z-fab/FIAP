/**
 * nav.js — Sistema de navegação do textbook
 *
 * Compartilhado por todas as páginas. Detecta automaticamente se está
 * sendo executado a partir do index (raiz do textbook) ou de um capítulo
 * (subdiretorio chapters/) e ajusta os caminhos de acordo.
 *
 * Uso em capítulos:
 *   <script src="../assets/js/nav.js"></script>
 *
 * Uso no index:
 *   <script src="assets/js/nav.js"></script>
 */

'use strict';

// ============================================================
// === Dados dos capítulos ===
// ============================================================

const CHAPTERS = [
  {
    id: '01',
    title: 'O Problema',
    subtitle: 'Por que servir agentes é diferente',
    path: 'chapters/01-the-problem.html',
  },
  {
    id: '02',
    title: 'Padrões de Comunicação',
    subtitle: 'Sync, Stream, Async',
    path: 'chapters/02-communication.html',
  },
  {
    id: '03',
    title: 'Controles de Produção',
    subtitle: 'Timeout, Concorrência, Resiliência',
    path: 'chapters/03-production.html',
  },
  {
    id: '04',
    title: 'Deploy',
    subtitle: 'Artesanal vs. Gerenciado',
    path: 'chapters/04-deploy.html',
  },
];

// ============================================================
// === Detecção de contexto (raiz vs chapters/) ===
// ============================================================

/**
 * Retorna true se a página atual está dentro do diretório chapters/.
 *
 * @returns {boolean}
 */
function isInChaptersDir() {
  return /\/chapters\//.test(window.location.pathname);
}

/**
 * Resolve o caminho de um capítulo relativo a página atual.
 *
 * @param {string} chapterPath - Caminho no formato 'chapters/XX-slug.html'
 * @returns {string}
 */
function resolveChapterPath(chapterPath) {
  if (isInChaptersDir()) {
    return chapterPath.replace(/^chapters\//, '');
  }
  return chapterPath;
}

/**
 * Resolve o caminho de um recurso de assets relativo a página atual.
 *
 * @param {string} assetPath - Caminho relativo ao index (ex: 'assets/css/style.css')
 * @returns {string}
 */
function resolveAssetPath(assetPath) {
  if (isInChaptersDir()) {
    return '../' + assetPath;
  }
  return assetPath;
}

// ============================================================
// === Detecção do capítulo atual ===
// ============================================================

/**
 * Retorna o índice (0-based) do capítulo atual com base na URL.
 * Retorna -1 se a página atual não for um capítulo.
 *
 * @returns {number}
 */
function getCurrentChapterIndex() {
  const pathname = window.location.pathname;

  for (let i = 0; i < CHAPTERS.length; i++) {
    const filename = CHAPTERS[i].path.replace(/^chapters\//, '');
    if (pathname.includes(filename)) {
      return i;
    }
  }

  return -1;
}

// ============================================================
// === Renderizacao da Sidebar ===
// ============================================================

/**
 * Cria um elemento com atributos opcionais (helper interno — sem innerHTML).
 */
function _el(tag, attrs, styles) {
  const el = document.createElement(tag);
  if (attrs) {
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') el.className = v;
      else if (k === 'textContent') el.textContent = v;
      else el.setAttribute(k, v);
    });
  }
  if (styles) el.style.cssText = styles;
  return el;
}

/**
 * Renderiza a lista de capítulos na sidebar fornecida.
 *
 * @param {HTMLElement} containerEl
 */
function renderSidebar(containerEl) {
  if (!containerEl) return;

  const currentIndex = getCurrentChapterIndex();
  const logoHref = isInChaptersDir() ? '../index.html' : 'index.html';

  // Header
  const header = _el('div', { class: 'sidebar-header' });

  const logoLink = _el('a', { href: logoHref, class: 'sidebar-logo', textContent: 'Do Script ao Serviço' }, 'text-decoration:none; color:inherit;');
  const sub = _el('div', { textContent: 'Deploy de Agentes LLM' });
  header.appendChild(logoLink);
  header.appendChild(sub);

  // Nav
  const nav = _el('nav', { class: 'sidebar-nav', 'aria-label': 'Capítulos' });

  const label = _el('div', { class: 'sidebar-nav-chapter', textContent: 'Capítulos' });
  nav.appendChild(label);

  const list = _el('ul', { class: 'sidebar-nav-list' });

  CHAPTERS.forEach(function(chapter, index) {
    const isActive = index === currentIndex;
    const href = resolveChapterPath(chapter.path);

    const li = _el('li', { class: 'sidebar-nav-item' });

    const a = _el('a', {
      href: href,
      class: 'sidebar-nav-link' + (isActive ? ' is-active' : ''),
      'aria-current': isActive ? 'page' : 'false',
    });

    const numSpan = _el('span', { textContent: chapter.id },
      'min-width:1.75rem; font-size:0.7rem; font-weight:700; color:var(--color-accent); font-family:var(--font-code);'
    );

    const textWrap = _el('span');
    const titleSpan = _el('span', { textContent: chapter.title }, 'display:block; font-weight:500;');
    const subtitleSpan = _el('span', { textContent: chapter.subtitle },
      'display:block; font-size:0.75rem; color:var(--color-text-secondary); font-weight:400;'
    );
    textWrap.appendChild(titleSpan);
    textWrap.appendChild(subtitleSpan);

    a.appendChild(numSpan);
    a.appendChild(textWrap);

    li.appendChild(a);
    list.appendChild(li);
  });

  nav.appendChild(list);

  // Footer
  const footer = _el('div', { textContent: 'FIAP — ML Engineering 2025' },
    'padding:var(--space-4); border-top:1px solid var(--color-border); font-size:0.7rem; color:var(--color-text-secondary); text-align:center;'
  );

  containerEl.appendChild(header);
  containerEl.appendChild(nav);
  containerEl.appendChild(footer);
}

// ============================================================
// === Navegação prev / next ===
// ============================================================

/**
 * Cria um SVG de seta (esquerda ou direita) para os botoes de nav.
 * Uso de createElementNS para SVG — sem innerHTML.
 *
 * @param {'left'|'right'} direction
 * @returns {SVGElement}
 */
function _arrowSvg(direction) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('width', '16');
  svg.setAttribute('height', '16');
  svg.setAttribute('viewBox', '0 0 16 16');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('aria-hidden', 'true');

  const path = document.createElementNS(ns, 'path');
  path.setAttribute('d', direction === 'left' ? 'M10 12L6 8l4-4' : 'M6 4l4 4-4 4');
  path.setAttribute('stroke', 'currentColor');
  path.setAttribute('stroke-width', '1.5');
  path.setAttribute('stroke-linecap', 'round');
  path.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(path);

  return svg;
}

/**
 * Renderiza os links de navegação anterior/próximo.
 *
 * @param {HTMLElement} containerEl
 */
function renderBottomNav(containerEl) {
  if (!containerEl) return;

  const currentIndex = getCurrentChapterIndex();
  if (currentIndex === -1) return;

  const prev = CHAPTERS[currentIndex - 1] || null;
  const next = CHAPTERS[currentIndex + 1] || null;

  const nav = _el('nav', { 'aria-label': 'Navegação entre capítulos' },
    'display:flex; justify-content:space-between; align-items:center; gap:var(--space-4); padding:var(--space-8) 0 var(--space-4); border-top:1px solid var(--color-border); margin-top:var(--space-12);'
  );

  // Slot anterior
  const prevSlot = _el('div', {}, 'flex:1;');

  if (prev) {
    const prevLink = _el('a', {
      href: resolveChapterPath(prev.path),
      class: 'btn btn--outline',
      'aria-label': 'Capítulo anterior: ' + prev.title,
    });

    prevLink.appendChild(_arrowSvg('left'));

    const prevText = _el('span');
    const prevLabel = _el('span', { textContent: 'Anterior' }, 'display:block; font-size:0.7rem; opacity:.7; font-weight:400;');
    const prevTitle = _el('span', { textContent: prev.title }, 'display:block;');
    prevText.appendChild(prevLabel);
    prevText.appendChild(prevTitle);
    prevLink.appendChild(prevText);

    prevSlot.appendChild(prevLink);
  }

  // Indicador de progresso
  const indicator = _el('div', {}, 'flex-shrink:0; display:flex; gap:var(--space-2); align-items:center;');
  CHAPTERS.forEach(function(_, i) {
    const dot = _el('span', {},
      'width:' + (i === currentIndex ? '20px' : '6px') + '; height:6px; border-radius:3px; ' +
      'background-color:' + (i === currentIndex ? 'var(--color-primary)' : 'var(--color-border)') + '; ' +
      'transition:width 200ms ease-out, background-color 200ms ease-out;'
    );
    indicator.appendChild(dot);
  });

  // Slot próximo
  const nextSlot = _el('div', {}, 'flex:1; display:flex; justify-content:flex-end;');

  if (next) {
    const nextLink = _el('a', {
      href: resolveChapterPath(next.path),
      class: 'btn btn--primary',
      'aria-label': 'Próximo capítulo: ' + next.title,
    });

    const nextText = _el('span');
    const nextLabel = _el('span', { textContent: 'Próximo' }, 'display:block; font-size:0.7rem; opacity:.85; font-weight:400;');
    const nextTitle = _el('span', { textContent: next.title }, 'display:block;');
    nextText.appendChild(nextLabel);
    nextText.appendChild(nextTitle);
    nextLink.appendChild(nextText);
    nextLink.appendChild(_arrowSvg('right'));

    nextSlot.appendChild(nextLink);
  }

  nav.appendChild(prevSlot);
  nav.appendChild(indicator);
  nav.appendChild(nextSlot);

  containerEl.appendChild(nav);
}

// ============================================================
// === Toggle da Sidebar (mobile) ===
// ============================================================

/**
 * Alterna a visibilidade da sidebar em dispositivos moveis.
 */
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  const isDesktop = window.matchMedia('(min-width: 1024px)').matches;

  if (!sidebar) return;

  const isOpen = sidebar.classList.contains('is-open');

  if (isOpen) {
    sidebar.classList.remove('is-open');
    if (!isDesktop && overlay) overlay.classList.remove('is-active');
    if (!isDesktop) document.body.style.overflow = '';
  } else {
    sidebar.classList.add('is-open');
    if (!isDesktop && overlay) overlay.classList.add('is-active');
    if (!isDesktop) document.body.style.overflow = 'hidden';
  }
}

// ============================================================
// === Atalhos de teclado ===
// ============================================================

/**
 * Configura navegação por teclado:
 *   ArrowLeft  — capítulo anterior
 *   ArrowRight — próximo capítulo
 */
function setupKeyboardShortcuts() {
  const currentIndex = getCurrentChapterIndex();
  if (currentIndex === -1) return;

  document.addEventListener('keydown', function(e) {
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return;
    if (document.activeElement && document.activeElement.isContentEditable) return;

    if (e.key === 'ArrowLeft' && !e.altKey && !e.ctrlKey && !e.metaKey) {
      const prev = CHAPTERS[currentIndex - 1];
      if (prev) window.location.href = resolveChapterPath(prev.path);
    }

    if (e.key === 'ArrowRight' && !e.altKey && !e.ctrlKey && !e.metaKey) {
      const next = CHAPTERS[currentIndex + 1];
      if (next) window.location.href = resolveChapterPath(next.path);
    }
  });
}

// ============================================================
// === Hamburguer SVG ===
// ============================================================

function _hamburgerSvg() {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('width', '18');
  svg.setAttribute('height', '18');
  svg.setAttribute('viewBox', '0 0 18 18');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('aria-hidden', 'true');

  [[4.5], [9], [13.5]].forEach(function(yArr) {
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', '2');
    line.setAttribute('y1', String(yArr[0]));
    line.setAttribute('x2', '16');
    line.setAttribute('y2', String(yArr[0]));
    line.setAttribute('stroke', 'currentColor');
    line.setAttribute('stroke-width', '1.5');
    line.setAttribute('stroke-linecap', 'round');
    svg.appendChild(line);
  });

  return svg;
}

// ============================================================
// === Inicialização ===
// ============================================================

/**
 * Ponto de entrada principal. Chamado automaticamente no DOMContentLoaded.
 */
function initNav() {
  // --- Sidebar ---
  let sidebar = document.querySelector('.sidebar');

  if (!sidebar) {
    sidebar = document.createElement('aside');
    sidebar.className = 'sidebar';

    const pageWrapper = document.querySelector('.page-wrapper');
    if (pageWrapper) {
      pageWrapper.insertBefore(sidebar, pageWrapper.firstChild);
    } else {
      document.body.insertBefore(sidebar, document.body.firstChild);
    }
  }

  if (sidebar.children.length === 0) {
    renderSidebar(sidebar);
  }

  // --- Overlay ---
  let overlay = document.querySelector('.sidebar-overlay');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
  }

  overlay.addEventListener('click', toggleSidebar);

  // --- Botao de toggle ---
  let toggleBtn = document.querySelector('.sidebar-toggle');

  if (!toggleBtn) {
    toggleBtn = _el('button', {
      class: 'sidebar-toggle',
      'aria-label': 'Abrir menu de navegação',
      'aria-expanded': 'false',
    });
    toggleBtn.appendChild(_hamburgerSvg());
    // Insere dentro do page-wrapper (após sidebar) para que os seletores
    // CSS de sibling (~) funcionem: .sidebar.is-open ~ .sidebar-toggle
    var pageWrapper = document.querySelector('.page-wrapper');
    if (pageWrapper) {
      pageWrapper.insertBefore(toggleBtn, sidebar.nextSibling);
    } else {
      document.body.appendChild(toggleBtn);
    }
  }

  toggleBtn.addEventListener('click', function() {
    toggleSidebar();
    const isOpen = sidebar.classList.contains('is-open');
    toggleBtn.setAttribute('aria-expanded', String(isOpen));
  });

  // No index não mostramos sidebar (só nos capítulos)
  const isIndex = getCurrentChapterIndex() === -1;

  if (isIndex) {
    sidebar.style.display = 'none';
    toggleBtn.style.display = 'none';
  }

  // Desktop: sidebar aberta por padrão nos capítulos
  const mq = window.matchMedia('(min-width: 1024px)');

  function applyDesktopLayout(matches) {
    if (isIndex) return; // Index nunca mostra sidebar
    if (matches) {
      sidebar.classList.remove('sidebar--visible');
      sidebar.classList.add('is-open');
      overlay.classList.remove('is-active');
      document.body.style.overflow = '';
    } else {
      sidebar.classList.remove('sidebar--visible');
      sidebar.classList.remove('is-open');
      document.body.style.overflow = '';
    }
  }

  applyDesktopLayout(mq.matches);
  mq.addEventListener('change', function(e) { applyDesktopLayout(e.matches); });

  // --- Navegação prev/next ---
  const contentInner = document.querySelector('.content-inner');
  if (contentInner) {
    renderBottomNav(contentInner);
  }

  // --- Atalhos de teclado ---
  setupKeyboardShortcuts();
}

// Auto-inicializa
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initNav);
} else {
  initNav();
}

// ============================================================
// === Exportacao global ===
// ============================================================

window.TextbookNav = {
  CHAPTERS: CHAPTERS,
  getCurrentChapterIndex: getCurrentChapterIndex,
  renderSidebar: renderSidebar,
  renderBottomNav: renderBottomNav,
  toggleSidebar: toggleSidebar,
  initNav: initNav,
  resolveChapterPath: resolveChapterPath,
  resolveAssetPath: resolveAssetPath,
};
