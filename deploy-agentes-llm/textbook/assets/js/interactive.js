/**
 * interactive.js — Utilitários compartilhados para componentes interativos do textbook.
 *
 * Cada capítulo tem seu próprio JS que importa estas funções via window.TextbookUtils.
 * Sem dependências externas — tudo vanilla JS.
 *
 * Uso:
 *   const { animateValue, formatBRL, RequestState } = window.TextbookUtils;
 */

'use strict';

// ============================================================
// === Animação ===
// ============================================================

/**
 * Anima um valor numérico em um elemento (countUp / countDown).
 *
 * @param {HTMLElement} element   - Elemento cujo textContent será atualizado.
 * @param {number}      start     - Valor inicial da animação.
 * @param {number}      end       - Valor final da animação.
 * @param {number}      [duration=1000] - Duração em milissegundos.
 * @param {Function}    [format]  - Função de formatação aplicada ao valor atual.
 *                                  Padrão: arredonda para inteiro.
 */
function animateValue(element, start, end, duration = 1000, format = (v) => Math.round(v)) {
  const startTime = performance.now();

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Easing ease-out: desacelera ao final da animação
    const eased = 1 - Math.pow(1 - progress, 3);

    const current = start + (end - start) * eased;
    element.textContent = format(current);

    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
}

/**
 * Aguarda N milissegundos (útil para animações sequenciais com async/await).
 *
 * @param {number} ms - Tempo de espera em milissegundos.
 * @returns {Promise<void>}
 */
function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============================================================
// === Debounce / Throttle ===
// ============================================================

/**
 * Retorna uma versão com debounce da função fornecida.
 * Ideal para sliders e inputs que disparam muitos eventos em sequência.
 *
 * @param {Function} fn        - Função a ser executada após o período de espera.
 * @param {number}   [wait=150] - Tempo de espera em milissegundos.
 * @returns {Function}
 */
function debounce(fn, wait = 150) {
  let timer = null;

  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, wait);
  };
}

// ============================================================
// === DOM Helpers ===
// ============================================================

/**
 * Cria um elemento HTML com classes e conteúdo opcionais.
 * O elemento não é inserido no DOM — apenas retornado.
 *
 * AVISO DE SEGURANÇA: o parâmetro `content` é inserido via innerHTML.
 * Use apenas com strings literais de conteúdo confiável (ex: strings
 * definidas no próprio código do capítulo). Nunca passe input do usuário.
 *
 * @param {string} tag           - Tag HTML (ex: 'div', 'span', 'button').
 * @param {string} [classNames=''] - Classes separadas por espaço.
 * @param {string} [content='']  - Conteúdo HTML confiável do elemento.
 * @returns {HTMLElement}
 */
function createElement(tag, classNames = '', content = '') {
  const el = document.createElement(tag);

  if (classNames) {
    // Suporta string com múltiplas classes separadas por espaço
    classNames.trim().split(/\s+/).forEach((cls) => {
      if (cls) el.classList.add(cls);
    });
  }

  if (content) {
    // Conteúdo deve ser sempre uma string literal confiável
    // (nunca input do usuário) para evitar XSS.
    el.innerHTML = content; // trusted-content-only
  }

  return el;
}

/**
 * Atalho para querySelector.
 *
 * @param {string}        selector - Seletor CSS.
 * @param {ParentNode}    [parent=document] - Escopo da busca.
 * @returns {Element|null}
 */
function $(selector, parent = document) {
  return parent.querySelector(selector);
}

/**
 * Atalho para querySelectorAll — retorna Array (não NodeList).
 *
 * @param {string}     selector - Seletor CSS.
 * @param {ParentNode} [parent=document] - Escopo da busca.
 * @returns {Element[]}
 */
function $$(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}

// ============================================================
// === Formatação ===
// ============================================================

/**
 * Formata um número como moeda brasileira (R$ 1.234,56).
 *
 * @param {number} value - Valor numérico a formatar.
 * @returns {string}
 */
function formatBRL(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Formata uma duração em milissegundos como string legível.
 * - Menor que 1000ms: exibe "XXXms"   (ex: "450ms")
 * - 1000ms ou mais:   exibe "X.Xs"    (ex: "1.5s")
 *
 * @param {number} ms - Duração em milissegundos.
 * @returns {string}
 */
function formatDuration(ms) {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Formata um número com separador de milhar conforme locale pt-BR.
 * Ex: 1234567 → "1.234.567"
 *
 * @param {number} value - Número a formatar.
 * @returns {string}
 */
function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value);
}

// ============================================================
// === Observadores ===
// ============================================================

/**
 * Executa um callback uma única vez quando o elemento entra no viewport.
 * Útil para auto-iniciar animações ao rolar a página.
 *
 * @param {Element}              element  - Elemento a observar.
 * @param {Function}             callback - Função chamada ao tornar-se visível.
 * @param {IntersectionObserverInit} [options] - Opções do IntersectionObserver.
 */
function onVisible(element, callback, options = { threshold: 0.3 }) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        callback(entry);
        observer.disconnect(); // Dispara apenas uma vez
      }
    });
  }, options);

  observer.observe(element);
}

// ============================================================
// === Estado ===
// ============================================================

/**
 * Máquina de estados simples para simulação de requisições HTTP.
 *
 * Estados possíveis:
 *   'idle'      — aguardando ser enfileirada
 *   'queued'    — na fila, não iniciada
 *   'waiting'   — aguardando slot disponível (ex: rate limit)
 *   'active'    — em processamento
 *   'completed' — concluída com sucesso
 *   'failed'    — falha durante processamento
 *   'rejected'  — rejeitada antes de iniciar (ex: circuit breaker)
 */
class RequestState {
  /**
   * @param {string|number} id - Identificador único da requisição.
   */
  constructor(id) {
    this.id = id;
    this.state = 'idle';
    this.startTime = null;
    this.endTime = null;
  }

  /**
   * Transita para um novo estado.
   * Registra timestamps automáticos para estados relevantes.
   *
   * @param {'idle'|'queued'|'waiting'|'active'|'completed'|'failed'|'rejected'} newState
   */
  transition(newState) {
    this.state = newState;

    if (newState === 'active') {
      this.startTime = Date.now();
    }

    if (['completed', 'failed', 'rejected'].includes(newState)) {
      this.endTime = Date.now();
    }
  }

  /**
   * Tempo decorrido desde que a requisição ficou ativa (em ms).
   * Se ainda estiver ativa, usa o momento atual como referência.
   *
   * @returns {number}
   */
  get elapsed() {
    if (!this.startTime) return 0;
    return (this.endTime || Date.now()) - this.startTime;
  }

  /**
   * Indica se a requisição chegou a um estado terminal
   * (não haverá mais transições).
   *
   * @returns {boolean}
   */
  get isTerminal() {
    return ['completed', 'failed', 'rejected'].includes(this.state);
  }
}

// ============================================================
// === Cores por estado (espelha o design system do CSS) ===
// ============================================================

/**
 * Mapa de cores por estado para uso em canvas, SVG ou estilos inline.
 * Os valores correspondem às variáveis CSS do tema escuro do textbook.
 *
 * @type {Record<string, string>}
 */
const STATE_COLORS = {
  idle:      '#94a3b8', // text-secondary
  queued:    '#94a3b8', // text-secondary
  waiting:   '#eab308', // warning  (amarelo)
  active:    '#22c55e', // success  (verde)
  completed: '#4F46E5', // primary  (violeta)
  failed:    '#ef4444', // error    (vermelho)
  rejected:  '#ef4444', // error    (vermelho)
};

// ============================================================
// === Exportação global (sem bundler — acesso via window) ===
// ============================================================

window.TextbookUtils = {
  // Animação
  animateValue,
  delay,

  // Debounce
  debounce,

  // DOM
  createElement,
  $,
  $$,

  // Formatação
  formatBRL,
  formatDuration,
  formatNumber,

  // Observadores
  onVisible,

  // Estado
  RequestState,
  STATE_COLORS,
};
