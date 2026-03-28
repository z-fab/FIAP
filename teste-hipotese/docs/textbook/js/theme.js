/**
 * Theme toggle - Dark/Light mode with sun/moon icons + label
 * Icons are INVERTED: moon shown in light mode (click→dark), sun in dark mode (click→light)
 * Label shows CURRENT state: "Claro" in light, "Escuro" in dark
 * Note: All innerHTML usage is with hardcoded SVG content only (no user input).
 */

const MOON_SVG = '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
const SUN_SVG = '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';

function getStoredTheme() {
  return localStorage.getItem('textbook-theme') || 'light';
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('textbook-theme', theme);
  updateToggleLabels(theme);
}

function updateToggleLabels(theme) {
  const label = theme === 'dark' ? 'Escuro' : 'Claro';
  document.querySelectorAll('.theme-toggle').forEach(btn => {
    const labelEl = btn.querySelector('.theme-label');
    if (labelEl) labelEl.textContent = label;
  });
}

function toggleTheme() {
  const current = getStoredTheme();
  setTheme(current === 'dark' ? 'light' : 'dark');
}

function injectToggleIcons() {
  const theme = getStoredTheme();
  const label = theme === 'dark' ? 'Escuro' : 'Claro';

  document.querySelectorAll('.theme-toggle').forEach(btn => {
    if (btn.querySelector('.icon-moon')) return; // already injected
    btn.textContent = '';
    btn.insertAdjacentHTML('beforeend', MOON_SVG + SUN_SVG + '<span class="theme-label">' + label + '</span>');
    btn.addEventListener('click', toggleTheme);
  });
}

// Apply theme before DOMContentLoaded to avoid flash
setTheme(getStoredTheme());

document.addEventListener('DOMContentLoaded', injectToggleIcons);
