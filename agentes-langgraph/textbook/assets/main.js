/* ═══════════════════════════════════════════════════════════
   Main JS — Agentes de IA Textbook
   Shared logic across all pages
   ═══════════════════════════════════════════════════════════ */

// Chapter registry
const CHAPTERS = [
  { id: '01', file: '01-o-que-sao-agentes.html', title: 'O que são Agentes de IA' },
  { id: '02', file: '02-raciocinio-e-tool-calling.html', title: 'Raciocínio e Tool Calling' },
  { id: '03', file: '03-context-engineering.html', title: 'Context Engineering' },
  { id: '04', file: '04-langgraph-na-pratica.html', title: 'LangGraph na Prática' },
];

// Copy button for code blocks
function initCopyButtons() {
  document.querySelectorAll('pre').forEach(pre => {
    if (pre.querySelector('.copy-btn')) return;
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copiar';
    btn.style.cssText = 'position:absolute;top:0.5rem;right:0.5rem;z-index:10;background:rgba(255,255,255,0.1);color:white;border:none;border-radius:4px;padding:0.25rem 0.75rem;font-size:0.75rem;cursor:pointer;font-family:var(--font-sans);transition:background 0.15s;';
    btn.addEventListener('click', () => {
      const code = pre.querySelector('code');
      navigator.clipboard.writeText(code ? code.textContent.trim() : pre.textContent.trim());
      btn.textContent = '✓ Copiado';
      setTimeout(() => { btn.textContent = 'Copiar'; }, 2000);
    });
    btn.addEventListener('mouseenter', () => { btn.style.background = 'rgba(255,255,255,0.2)'; });
    btn.addEventListener('mouseleave', () => { btn.style.background = 'rgba(255,255,255,0.1)'; });
    pre.style.position = 'relative';
    pre.appendChild(btn);
  });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initCopyButtons();
});
