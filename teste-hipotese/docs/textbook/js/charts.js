/**
 * Chart.js utilities and shared chart configurations
 * Colors aligned with design system
 */

const CHART_COLORS = {
  primary: '#8b5cf6',
  secondary: '#7c3aed',
  success: '#4caf7d',
  danger: '#d4556b',
  warning: '#e0a633',
  info: '#4a8eb8',
  muted: '#8a8a9a',
  accent2: '#e67e5a',
  accent3: '#50b5a0',
};

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        font: { family: "'Lato', sans-serif", size: 13 },
        usePointStyle: true,
        padding: 16,
      },
    },
    tooltip: {
      backgroundColor: 'rgba(30, 30, 47, 0.92)',
      titleFont: { family: "'Lato', sans-serif", size: 13 },
      bodyFont: { family: "'JetBrains Mono', monospace", size: 12 },
      cornerRadius: 8,
      padding: 10,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { family: "'Lato', sans-serif", size: 12 } },
    },
    y: {
      grid: { color: 'rgba(0, 0, 0, 0.04)' },
      ticks: { font: { family: "'Lato', sans-serif", size: 12 } },
    },
  },
};

/**
 * Normal distribution PDF
 */
function normalPDF(x, mean, std) {
  const exp = -0.5 * ((x - mean) / std) ** 2;
  return (1 / (std * Math.sqrt(2 * Math.PI))) * Math.exp(exp);
}

/**
 * Generate x values for a range
 */
function linspace(start, end, n) {
  const step = (end - start) / (n - 1);
  return Array.from({ length: n }, (_, i) => start + i * step);
}

/**
 * Normal CDF approximation (Abramowitz and Stegun)
 */
function normalCDF(x) {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  x = Math.abs(x) / Math.SQRT2;

  const t = 1.0 / (1.0 + p * x);
  const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

  return 0.5 * (1.0 + sign * y);
}

/**
 * Draw a filled area under curve on canvas
 */
function drawFilledCurve(ctx, xPixels, yPixels, baseY, fillColor) {
  ctx.beginPath();
  ctx.moveTo(xPixels[0], baseY);
  for (let i = 0; i < xPixels.length; i++) {
    ctx.lineTo(xPixels[i], yPixels[i]);
  }
  ctx.lineTo(xPixels[xPixels.length - 1], baseY);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();
}

/**
 * Draw a curve line on canvas
 */
function drawCurve(ctx, xPixels, yPixels, strokeColor, lineWidth = 2) {
  ctx.beginPath();
  ctx.moveTo(xPixels[0], yPixels[0]);
  for (let i = 1; i < xPixels.length; i++) {
    ctx.lineTo(xPixels[i], yPixels[i]);
  }
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
}

/**
 * Make a canvas responsive - call on load and resize
 */
function makeCanvasResponsive(canvas, drawFn) {
  const container = canvas.parentElement;

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    const w = rect.width;
    const h = canvas.dataset.height ? parseInt(canvas.dataset.height) : Math.min(w * 0.55, 400);

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    // Store logical dimensions
    canvas._logicalWidth = w;
    canvas._logicalHeight = h;

    drawFn(ctx, w, h);
  }

  resize();
  window.addEventListener('resize', resize);
  return resize;
}

/**
 * Get theme-aware colors
 */
function getThemeColors() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    text: isDark ? '#d8d8e8' : '#2d2d3a',
    textMuted: isDark ? '#6a6a80' : '#8a8a9a',
    grid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
    bg: isDark ? '#141420' : '#faf9f7',
    primary: CHART_COLORS.primary,
    danger: CHART_COLORS.danger,
    success: CHART_COLORS.success,
    warning: CHART_COLORS.warning,
    info: CHART_COLORS.info,
    secondary: CHART_COLORS.secondary,
  };
}
