/**
 * Navigation - Sidebar, prev/next, mobile menu, progress bar
 * Note: All innerHTML usage is with hardcoded content only (no user input).
 */

const PAGES = [
  { id: '01-intro', title: 'Por que Teste de Hipótese?', number: '1' },
  { id: '02-concepts', title: 'Conceitos Fundamentais', number: '2' },
  { id: '03-workflow', title: 'O Fluxo Completo', number: '3' },
  { id: '04-tests', title: 'Testes Estatísticos', number: '4' },
  { id: '05-interpretation', title: 'Interpretação de Resultados', number: '5' },
  { id: '06-pitfalls', title: 'Armadilhas Comuns', number: '6' },
];

function getCurrentPageId() {
  const path = window.location.pathname;
  const filename = path.split('/').pop().replace('.html', '');
  return filename;
}

function buildSidebarNav() {
  const nav = document.querySelector('.sidebar-nav');
  if (!nav) return;

  const currentId = getCurrentPageId();
  const isInPages = window.location.pathname.includes('/pages/');

  // Clear existing content
  while (nav.firstChild) nav.removeChild(nav.firstChild);

  PAGES.forEach(page => {
    const a = document.createElement('a');
    a.href = isInPages ? `${page.id}.html` : `pages/${page.id}.html`;
    if (currentId === page.id) a.className = 'active';

    const span = document.createElement('span');
    span.className = 'nav-number';
    span.textContent = page.number;

    a.appendChild(span);
    a.appendChild(document.createTextNode(' ' + page.title));
    nav.appendChild(a);
  });
}

function buildPageNav() {
  const pageNav = document.querySelector('.page-nav');
  if (!pageNav) return;

  const currentId = getCurrentPageId();
  const currentIdx = PAGES.findIndex(p => p.id === currentId);
  const isInPages = window.location.pathname.includes('/pages/');
  const prefix = isInPages ? '' : 'pages/';

  while (pageNav.firstChild) pageNav.removeChild(pageNav.firstChild);

  // Previous
  if (currentIdx > 0) {
    const prev = PAGES[currentIdx - 1];
    const a = document.createElement('a');
    a.href = `${prefix}${prev.id}.html`;
    const labelDiv = document.createElement('div');
    labelDiv.className = 'nav-label';
    labelDiv.textContent = 'Anterior';
    const titleDiv = document.createElement('div');
    titleDiv.textContent = prev.title;
    a.appendChild(labelDiv);
    a.appendChild(titleDiv);
    pageNav.appendChild(a);
  } else {
    pageNav.appendChild(document.createElement('div'));
  }

  // Next
  if (currentIdx < PAGES.length - 1) {
    const next = PAGES[currentIdx + 1];
    const a = document.createElement('a');
    a.href = `${prefix}${next.id}.html`;
    const labelDiv = document.createElement('div');
    labelDiv.className = 'nav-label';
    labelDiv.textContent = 'Próximo';
    const titleDiv = document.createElement('div');
    titleDiv.textContent = next.title;
    a.appendChild(labelDiv);
    a.appendChild(titleDiv);
    pageNav.appendChild(a);
  } else {
    pageNav.appendChild(document.createElement('div'));
  }
}

function updateProgressBar() {
  const currentId = getCurrentPageId();
  const currentIdx = PAGES.findIndex(p => p.id === currentId);
  const progress = ((currentIdx + 1) / PAGES.length) * 100;

  const fill = document.querySelector('.progress-bar-fill');
  if (fill) {
    fill.style.width = `${progress}%`;
  }
}

function updateBreadcrumb() {
  const breadcrumb = document.querySelector('.breadcrumb');
  if (!breadcrumb) return;

  const currentId = getCurrentPageId();
  const currentPage = PAGES.find(p => p.id === currentId);
  const isInPages = window.location.pathname.includes('/pages/');
  const indexPath = isInPages ? '../index.html' : 'index.html';

  while (breadcrumb.firstChild) breadcrumb.removeChild(breadcrumb.firstChild);

  const link = document.createElement('a');
  link.href = indexPath;
  link.textContent = 'Início';
  breadcrumb.appendChild(link);

  if (currentPage) {
    breadcrumb.appendChild(document.createTextNode(' / ' + currentPage.title));
  }
}

function setupMobileMenu() {
  const toggles = document.querySelectorAll('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');

  if (sidebar) {
    toggles.forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('open');
      });
    });

    if (overlay) {
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
      });
    }

    // Close sidebar when clicking a nav link
    sidebar.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        sidebar.classList.remove('open');
      });
    });
  }
}

function setupKeyboardNav() {
  document.addEventListener('keydown', (e) => {
    // Don't navigate if user is typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    const currentId = getCurrentPageId();
    const currentIdx = PAGES.findIndex(p => p.id === currentId);
    const isInPages = window.location.pathname.includes('/pages/');
    const prefix = isInPages ? '' : 'pages/';

    if (e.key === 'ArrowRight' && currentIdx < PAGES.length - 1) {
      window.location.href = `${prefix}${PAGES[currentIdx + 1].id}.html`;
    } else if (e.key === 'ArrowLeft' && currentIdx > 0) {
      window.location.href = `${prefix}${PAGES[currentIdx - 1].id}.html`;
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  buildSidebarNav();
  buildPageNav();
  updateProgressBar();
  updateBreadcrumb();
  setupMobileMenu();
  setupKeyboardNav();
});
