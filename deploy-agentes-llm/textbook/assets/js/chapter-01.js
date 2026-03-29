/**
 * chapter-01.js — Componentes interativos do Capitulo 01:
 * "O Problema: Por que Servir Agentes e Diferente"
 *
 * Dois componentes:
 *   1. Diagrama Notebook vs. Producao (gap-diagram) — layout vertical
 *   2. Simulador de Carga (user-simulator) — teste de carga animado com canvas
 */

'use strict';

(function () {
  var U = window.TextbookUtils;
  var createElement = U.createElement;
  var $ = U.$;

  // ============================================================
  // === Diagrama Notebook vs. Producao ===
  // ============================================================

  var GAP_ITEMS = [
    {
      title: 'API com contrato',
      desc: 'Outros sistemas precisam chamar o agente via HTTP com schemas bem definidos. Não dá pra importar um módulo Python e chamar uma função — é preciso um endpoint com request/response documentados.',
    },
    {
      title: 'Streaming SSE',
      desc: 'Sem feedback intermediário, o usuário fica olhando uma tela branca por 30+ segundos. Server-Sent Events resolve mostrando o progresso em tempo real conforme o agente executa cada step.',
    },
    {
      title: 'Fila assíncrona',
      desc: 'Quando o processamento pode levar minutos, manter a conexão HTTP aberta é frágil. Uma fila desacopla quem envia de quem processa e permite retry sem retrabalho.',
    },
    {
      title: 'Timeout em camadas',
      desc: 'Um timeout único não funciona: o LLM pode demorar, mas a tool call pode travar. Cada camada (HTTP, agente, tool) precisa do seu próprio limite, com fallback adequado.',
    },
    {
      title: 'Controle de concorrência',
      desc: 'Sem semáforo, 100 requests simultâneas disparam 100 chamadas ao LLM. Além de estourar rate limits do provider, o custo escala sem controle.',
    },
    {
      title: 'Erros tipados',
      desc: 'Retornar HTTP 500 para tudo impede o cliente de tomar decisões. Erros tipados (timeout, rate_limit, partial_failure) permitem retry seletivo e fallback inteligente.',
    },
    {
      title: 'Health checks',
      desc: 'O orquestrador (Kubernetes, load balancer) precisa saber se o serviço está saudável. Um health check que verifica conectividade com o LLM evita rotear tráfego para pods quebrados.',
    },
    {
      title: 'Logging estruturado',
      desc: 'print() não escala. Logs em JSON com trace_id, duração e contagem de tokens permitem debugging, alertas automáticos e dashboards de custo.',
    },
    {
      title: 'Container + deploy',
      desc: 'O agente precisa rodar em qualquer ambiente de forma reproduzível. Um Dockerfile com dependências fixas e um pipeline de CI/CD garantem que o que funciona local funciona em produção.',
    },
  ];

  function createChevronSvg() {
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('class', 'gap-item-chevron');
    svg.setAttribute('width', '16');
    svg.setAttribute('height', '16');
    svg.setAttribute('viewBox', '0 0 16 16');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('aria-hidden', 'true');

    var path = document.createElementNS(ns, 'path');
    path.setAttribute('d', 'M6 4l4 4-4 4');
    path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '1.5');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(path);

    return svg;
  }

  function initGapDiagram() {
    var container = $('#gap-diagram');
    if (!container) return;

    // --- Notebook card ---
    var nbLabel = createElement('div', 'gap-section-label gap-section-label--notebook', 'Notebook');
    container.appendChild(nbLabel);

    var notebookBox = createElement('div', 'gap-notebook-box');
    var lines = [
      'python agent.run()',
      'print(result)',
      '',
      '1 usuário',
      'sem timeout',
      'sem controle de custo',
    ];
    lines.forEach(function (line) {
      var span = document.createElement('span');
      span.textContent = line || '\u00A0';
      notebookBox.appendChild(span);
    });
    container.appendChild(notebookBox);

    // --- Arrow divider ---
    var arrow = createElement('div', 'gap-arrow');
    var arrowLine1 = createElement('div', 'gap-arrow-line');
    var arrowLabel = createElement('div', 'gap-arrow-label', 'O que falta para produção?');
    var arrowChevron = createElement('div', 'gap-arrow-chevron');
    arrow.appendChild(arrowLine1);
    arrow.appendChild(arrowLabel);
    arrow.appendChild(arrowChevron);
    container.appendChild(arrow);

    // --- Production accordion items (full width, vertical stack) ---
    var prodLabel = createElement('div', 'gap-section-label gap-section-label--prod', 'Producao');
    container.appendChild(prodLabel);

    GAP_ITEMS.forEach(function (item) {
      var wrapper = createElement('div', 'gap-item');

      var trigger = document.createElement('button');
      trigger.className = 'gap-item-trigger';
      trigger.setAttribute('aria-expanded', 'false');

      var titleSpan = document.createElement('span');
      titleSpan.textContent = item.title;
      trigger.appendChild(titleSpan);
      trigger.appendChild(createChevronSvg());

      var body = createElement('div', 'gap-item-body');
      var content = createElement('div', 'gap-item-content', item.desc);
      body.appendChild(content);

      trigger.addEventListener('click', function () {
        var isOpen = wrapper.classList.contains('is-open');
        if (isOpen) {
          wrapper.classList.remove('is-open');
          trigger.setAttribute('aria-expanded', 'false');
        } else {
          wrapper.classList.add('is-open');
          trigger.setAttribute('aria-expanded', 'true');
        }
      });

      wrapper.appendChild(trigger);
      wrapper.appendChild(body);
      container.appendChild(wrapper);
    });
  }

  // ============================================================
  // === Simulador de Carga — Teste de carga animado ===
  // ============================================================

  // --- Data generation models ---
  function generateLatencyData(users) {
    var p50 = 2000 + users * 30 + Math.pow(users / 50, 2) * 500;
    var p95 = 4000 + users * 80 + Math.pow(users / 40, 2) * 2000;
    var p99 = 6000 + users * 150 + Math.pow(users / 30, 3) * 1000;
    return { p50: p50, p95: p95, p99: p99 };
  }

  function generateThroughput(users) {
    if (users < 50) return users * 2;
    return 100 - (users - 50) * 0.8;
  }

  function generateErrorRate(users) {
    if (users < 30) return 0;
    if (users < 50) return (users - 30) * 0.5;
    return 10 + Math.pow((users - 50) / 10, 2) * 5;
  }

  // --- Canvas chart drawing with retina support ---
  function setupCanvas(canvas) {
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    var ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    return { ctx: ctx, w: rect.width, h: rect.height };
  }

  function drawChart(canvas, options) {
    var setup = setupCanvas(canvas);
    var ctx = setup.ctx;
    var w = setup.w;
    var h = setup.h;
    var maxX = options.maxX;
    var maxY = options.maxY;
    var chartLines = options.lines;
    var yLabel = options.yLabel || '';
    var padLeft = 45;
    var padBottom = 22;
    var padTop = 8;
    var padRight = 8;
    var chartW = w - padLeft - padRight;
    var chartH = h - padTop - padBottom;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = 'rgba(15, 23, 42, 0.3)';
    ctx.fillRect(0, 0, w, h);

    // Grid lines (horizontal)
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.5)';
    ctx.lineWidth = 0.5;
    var gridCount = 4;
    var g, gy, yVal;
    for (g = 0; g <= gridCount; g++) {
      gy = padTop + (chartH / gridCount) * g;
      ctx.beginPath();
      ctx.moveTo(padLeft, gy);
      ctx.lineTo(w - padRight, gy);
      ctx.stroke();

      // Y-axis labels
      yVal = maxY - (maxY / gridCount) * g;
      ctx.fillStyle = 'rgba(148, 163, 184, 0.7)';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      if (yVal >= 1000) {
        ctx.fillText((yVal / 1000).toFixed(0) + 'k', padLeft - 6, gy);
      } else {
        ctx.fillText(yVal.toFixed(0), padLeft - 6, gy);
      }
    }

    // X-axis label
    ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.font = '9px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('Usuarios', padLeft + chartW / 2, h - 10);

    // Y-axis label
    if (yLabel) {
      ctx.save();
      ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
      ctx.font = '9px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.translate(10, padTop + chartH / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(yLabel, 0, 0);
      ctx.restore();
    }

    // Draw lines
    chartLines.forEach(function (line) {
      if (line.data.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = line.color;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      line.data.forEach(function (point, i) {
        var x = padLeft + (point.x / maxX) * chartW;
        var y = padTop + chartH - (Math.min(point.y, maxY) / maxY) * chartH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });
  }

  function initUserSimulator() {
    var container = $('#user-simulator');
    if (!container) return;

    // Title
    var title = createElement('div', 'interactive-title', 'Teste de Carga: O que acontece quando o tráfego aumenta?');
    container.appendChild(title);

    // User counter
    var userCounter = createElement('div', 'sim-user-counter');
    var ucText = document.createTextNode('Usuários ativos: ');
    var ucSpan = document.createElement('span');
    ucSpan.id = 'sim-active-users';
    ucSpan.textContent = '0';
    userCounter.appendChild(ucText);
    userCounter.appendChild(ucSpan);
    container.appendChild(userCounter);

    // Controls
    var controls = createElement('div', 'sim-controls');
    var btnStart = document.createElement('button');
    btnStart.className = 'btn btn--primary';
    btnStart.textContent = 'Iniciar Teste de Carga';
    btnStart.id = 'sim-btn-start';

    var btnReset = document.createElement('button');
    btnReset.className = 'btn btn--outline';
    btnReset.textContent = 'Resetar';
    btnReset.id = 'sim-btn-reset';
    btnReset.disabled = true;

    controls.appendChild(btnStart);
    controls.appendChild(btnReset);
    container.appendChild(controls);

    // Callout area (between controls and grid)
    var calloutArea = document.createElement('div');
    calloutArea.id = 'sim-callout-area';
    calloutArea.style.cssText = 'margin-bottom: var(--space-4); min-height: 0;';
    container.appendChild(calloutArea);

    // 2x2 grid
    var grid = createElement('div', 'sim-grid');

    // Panel 1: Latência
    var panel1 = createElement('div', 'sim-panel');
    var panel1Title = createElement('div', 'sim-panel-title', 'Latência (ms)');
    var canvas1 = document.createElement('canvas');
    canvas1.className = 'sim-chart';
    canvas1.id = 'sim-chart-latency';

    var legend1 = createElement('div', 'sim-legend');
    var legendItems = [
      { color: '#22c55e', label: 'p50' },
      { color: '#eab308', label: 'p95' },
      { color: '#ef4444', label: 'p99' },
    ];
    legendItems.forEach(function (item) {
      var span = document.createElement('span');
      var dot = document.createElement('span');
      dot.className = 'sim-legend-dot';
      dot.style.backgroundColor = item.color;
      span.appendChild(dot);
      span.appendChild(document.createTextNode(item.label));
      legend1.appendChild(span);
    });

    panel1.appendChild(panel1Title);
    panel1.appendChild(canvas1);
    panel1.appendChild(legend1);
    grid.appendChild(panel1);

    // Panel 2: Throughput
    var panel2 = createElement('div', 'sim-panel');
    var panel2Title = createElement('div', 'sim-panel-title', 'Throughput (req/min)');
    var canvas2 = document.createElement('canvas');
    canvas2.className = 'sim-chart';
    canvas2.id = 'sim-chart-throughput';
    panel2.appendChild(panel2Title);
    panel2.appendChild(canvas2);
    grid.appendChild(panel2);

    // Panel 3: Error rate
    var panel3 = createElement('div', 'sim-panel');
    var panel3Title = createElement('div', 'sim-panel-title', 'Taxa de Erros (%)');
    var canvas3 = document.createElement('canvas');
    canvas3.className = 'sim-chart';
    canvas3.id = 'sim-chart-errors';
    panel3.appendChild(panel3Title);
    panel3.appendChild(canvas3);
    grid.appendChild(panel3);

    // Panel 4: Log de Erros
    var panel4 = createElement('div', 'sim-panel');
    var panel4Title = createElement('div', 'sim-panel-title', 'Log de Erros');
    var logContainer = document.createElement('div');
    logContainer.id = 'sim-error-log';
    logContainer.style.cssText = 'font-family: var(--font-code); font-size: 0.7rem; ' +
      'line-height: 1.6; max-height: 180px; overflow-y: auto; color: var(--color-text-secondary); ' +
      'padding: var(--space-2);';
    panel4.appendChild(panel4Title);
    panel4.appendChild(logContainer);
    grid.appendChild(panel4);

    container.appendChild(grid);

    // --- Log entries definition ---
    var LOG_ENTRIES = [
      { users: 10, level: 'INFO', color: '#22c55e', bold: false, text: '10 usuários ativos \u2014 latência estável' },
      { users: 25, level: 'WARN', color: '#eab308', bold: false, text: 'p95 ultrapassou 10s \u2014 considere habilitar streaming' },
      { users: 35, level: 'WARN', color: '#eab308', bold: false, text: 'p99 > 20s \u2014 timeouts de API Gateway prováveis' },
      { users: 45, level: 'ERROR', color: '#ef4444', bold: false, text: 'Rate limit do LLM atingido \u2014 requests sendo rejeitadas' },
      { users: 55, level: 'ERROR', color: '#ef4444', bold: false, text: 'Timeout em cascata \u2014 3 requests falharam simultaneamente' },
      { users: 65, level: 'ERROR', color: '#ef4444', bold: false, text: 'Worker pool esgotado \u2014 novas requests enfileiradas' },
      { users: 75, level: 'CRIT', color: '#ff3333', bold: true, text: 'Memória do worker acima de 90% \u2014 OOM iminente' },
      { users: 85, level: 'CRIT', color: '#ff3333', bold: true, text: 'Health check falhou \u2014 load balancer removendo instância' },
      { users: 95, level: 'CRIT', color: '#ff3333', bold: true, text: 'Serviço degradado \u2014 taxa de erro acima de 50%' },
    ];

    // --- Breakpoints definition ---
    var BREAKPOINTS = [
      {
        users: 1,
        type: 'info',
        title: 'Ponto de partida',
        text: 'Com 1 usuário, o agente responde em ~3s. A latência é estável e previsível. Este é o cenário do notebook \u2014 tudo funciona bem.',
        triggered: false,
      },
      {
        users: 25,
        type: 'warning',
        title: 'Latência começando a degradar',
        text: 'Com 25 usuários, o p95 já ultrapassa 10 segundos. Isso significa que 5% das requests demoram mais que o timeout padrão de muitos API Gateways (como o da AWS, que tem limite fixo de 29s). Observe como o p50 ainda parece aceitável \u2014 é o p95/p99 que revela o problema real.',
        triggered: false,
      },
      {
        users: 50,
        type: 'warning',
        title: 'Rate limit e saturação',
        text: 'Com 50 usuários simultâneos, o throughput parou de crescer e começou a cair. O LLM tem um rate limit \u2014 não adianta enviar mais requests, elas ficam na fila ou são rejeitadas. Note que a taxa de erros começa a subir. Sem um semáforo de concorrência, o sistema aceita tudo e falha para todos.',
        triggered: false,
      },
      {
        users: 75,
        type: 'danger',
        title: 'Colapso do sistema',
        text: 'Com 75 usuários, a latência p99 está acima de 45s, a taxa de erros ultrapassou 30%, e o throughput caiu pela metade. O sistema está em cascata de falhas: requests lentas ocupam workers, novas requests esperam, timeouts disparam, retries amplificam a carga. Este é o cenário que os controles de produção do Estágio 04 resolvem.',
        triggered: false,
      },
      {
        users: 100,
        type: 'danger',
        title: 'Resultado final',
        text: null,
        triggered: false,
      },
    ];

    // ---- Simulation state ----
    var simData = {
      latencyP50: [],
      latencyP95: [],
      latencyP99: [],
      throughput: [],
      errors: [],
      currentUsers: 0,
      running: false,
      animFrameId: null,
      startTime: 0,
      lastTickUsers: -1,
      resumeFromProgress: 0,
      logsShown: {},
    };

    var DURATION_MS = 15000;
    var MAX_USERS = 100;

    function clearCanvases() {
      [canvas1, canvas2, canvas3].forEach(function (c) {
        var s = setupCanvas(c);
        s.ctx.clearRect(0, 0, s.w, s.h);
      });
    }

    function addLogEntry(entry) {
      var log = document.getElementById('sim-error-log');
      var line = document.createElement('div');
      var prefix = document.createElement('span');
      prefix.style.color = entry.color;
      if (entry.bold) prefix.style.fontWeight = '700';
      prefix.textContent = '[' + entry.level + '] ';
      line.appendChild(prefix);
      line.appendChild(document.createTextNode(entry.text));
      log.appendChild(line);
      log.scrollTop = log.scrollHeight;
    }

    function showBreakpointCallout(bp) {
      var area = document.getElementById('sim-callout-area');
      area.innerHTML = '';

      var callout = createElement('div', 'callout callout--' + bp.type);
      callout.style.animation = 'fadeIn 300ms ease-out';
      var ctitle = createElement('div', 'callout-title', bp.title);
      var ctext = document.createElement('p');
      ctext.textContent = bp.text;
      callout.appendChild(ctitle);
      callout.appendChild(ctext);
      area.appendChild(callout);
    }

    function hideCallout() {
      var area = document.getElementById('sim-callout-area');
      area.innerHTML = '';
    }

    function resetSim() {
      if (simData.animFrameId) {
        cancelAnimationFrame(simData.animFrameId);
      }
      simData.latencyP50 = [];
      simData.latencyP95 = [];
      simData.latencyP99 = [];
      simData.throughput = [];
      simData.errors = [];
      simData.currentUsers = 0;
      simData.running = false;
      simData.animFrameId = null;
      simData.startTime = 0;
      simData.lastTickUsers = -1;
      simData.resumeFromProgress = 0;
      simData.logsShown = {};

      // Reset breakpoints
      for (var i = 0; i < BREAKPOINTS.length; i++) {
        BREAKPOINTS[i].triggered = false;
      }

      document.getElementById('sim-active-users').textContent = '0';

      // Clear error log
      var log = document.getElementById('sim-error-log');
      while (log.firstChild) {
        log.removeChild(log.firstChild);
      }

      // Clear callout
      hideCallout();

      btnStart.textContent = 'Iniciar Teste de Carga';
      btnStart.disabled = false;
      btnReset.disabled = true;

      clearCanvases();
    }

    function redrawAllCharts() {
      drawChart(canvas1, {
        maxX: 100,
        maxY: 60000,
        yLabel: 'ms',
        lines: [
          { color: '#22c55e', data: simData.latencyP50 },
          { color: '#eab308', data: simData.latencyP95 },
          { color: '#ef4444', data: simData.latencyP99 },
        ],
      });

      drawChart(canvas2, {
        maxX: 100,
        maxY: 120,
        yLabel: 'req/min',
        lines: [
          { color: '#22c55e', data: simData.throughput },
        ],
      });

      drawChart(canvas3, {
        maxX: 100,
        maxY: 80,
        yLabel: '%',
        lines: [
          { color: '#ef4444', data: simData.errors },
        ],
      });
    }

    function tick(timestamp) {
      if (!simData.startTime) simData.startTime = timestamp;
      var elapsed = timestamp - simData.startTime;
      var progressDelta = elapsed / DURATION_MS;
      var progress = Math.min(simData.resumeFromProgress + progressDelta, 1);
      var users = Math.round(progress * MAX_USERS);
      simData.currentUsers = users;

      // Update user counter
      document.getElementById('sim-active-users').textContent = String(users);

      // Only add data points when user count changes
      if (users > 0 && users !== simData.lastTickUsers) {
        simData.lastTickUsers = users;
        var lat = generateLatencyData(users);
        simData.latencyP50.push({ x: users, y: lat.p50 });
        simData.latencyP95.push({ x: users, y: lat.p95 });
        simData.latencyP99.push({ x: users, y: lat.p99 });
        simData.throughput.push({ x: users, y: Math.max(0, generateThroughput(users)) });
        simData.errors.push({ x: users, y: generateErrorRate(users) });
      }

      // Draw charts
      redrawAllCharts();

      // Check log entries
      for (var l = 0; l < LOG_ENTRIES.length; l++) {
        var le = LOG_ENTRIES[l];
        if (users >= le.users && !simData.logsShown[le.users]) {
          simData.logsShown[le.users] = true;
          addLogEntry(le);
        }
      }

      // Check breakpoints
      for (var i = 0; i < BREAKPOINTS.length; i++) {
        var bp = BREAKPOINTS[i];
        if (users >= bp.users && !bp.triggered) {
          bp.triggered = true;

          // Pause simulation
          simData.running = false;
          cancelAnimationFrame(simData.animFrameId);
          simData.animFrameId = null;

          // Store progress for resume
          simData.resumeFromProgress = progress;
          simData.startTime = 0;

          if (bp.users === 100) {
            // Final: generate dynamic text
            var finalLat = generateLatencyData(100);
            var finalErr = generateErrorRate(100);
            var finalTp = generateThroughput(100);
            bp.text = 'Com 100 usuários simultâneos, a latência p99 atingiu ' +
              (finalLat.p99 / 1000).toFixed(1) + 's, ' +
              'a taxa de erro chegou a ' + finalErr.toFixed(1) + '%, ' +
              'e o throughput caiu para ' + Math.max(0, finalTp).toFixed(0) + ' req/min. ' +
              'Sem controle de concorrência e estratégia de backpressure, o sistema colapsa.';
            showBreakpointCallout(bp);
            btnStart.textContent = 'Simulação concluída';
            btnStart.disabled = true;
          } else {
            showBreakpointCallout(bp);
            btnStart.textContent = 'Continuar \u2192';
            btnStart.disabled = false;
          }
          btnReset.disabled = false;
          return; // Stop the animation loop
        }
      }

      if (progress < 1) {
        simData.animFrameId = requestAnimationFrame(tick);
      } else {
        // Safety: simulation complete without hitting final breakpoint
        simData.running = false;
        btnStart.textContent = 'Simulação concluída';
        btnStart.disabled = true;
        btnReset.disabled = false;
      }
    }

    btnStart.addEventListener('click', function () {
      if (!simData.running && simData.currentUsers === 0) {
        // Fresh start
        resetSim();
        simData.running = true;
        btnStart.textContent = 'Simulando...';
        btnStart.disabled = true;
        btnReset.disabled = false;
        simData.animFrameId = requestAnimationFrame(tick);
      } else if (!simData.running && simData.currentUsers > 0) {
        // Continue after breakpoint
        hideCallout();
        simData.running = true;
        simData.startTime = 0;
        btnStart.textContent = 'Simulando...';
        btnStart.disabled = true;
        simData.animFrameId = requestAnimationFrame(tick);
      }
    });

    btnReset.addEventListener('click', resetSim);

    // Redraw charts on window resize
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        if (simData.latencyP50.length > 0) {
          redrawAllCharts();
        }
      }, 150);
    });
  }

  // ============================================================
  // === Inicializacao ===
  // ============================================================

  document.addEventListener('DOMContentLoaded', function () {
    initGapDiagram();
    initUserSimulator();
  });
})();
