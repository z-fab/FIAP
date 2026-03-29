/**
 * chapter-02.js — Interatividade do Capitulo 02: Padroes de Comunicacao
 *
 * Componentes:
 *   1. Pattern Comparator — simulacao lado a lado de Sync, Stream e Async
 *   2. SSE Timeline — eventos aparecendo sequencialmente
 *   (Architecture diagrams are now declarative SVGs in the HTML)
 *
 * Todas as strings passadas a createElement().content sao literais do proprio
 * codigo (trusted-content-only), conforme documentado em interactive.js.
 */

'use strict';

(function () {
  var TU = window.TextbookUtils;
  var $ = TU.$;
  var createElement = TU.createElement;
  var delay = TU.delay;
  var onVisible = TU.onVisible;

  // ============================================================
  // === 1. Pattern Comparator ===
  // ============================================================

  function initPatternComparator() {
    var container = $('#pattern-comparator');
    if (!container) return;

    // Title and description
    var title = createElement('div', 'interactive-title', 'Comparador de Padroes');
    var desc = createElement('div', 'interactive-description',
      'Clique em "Enviar Request" para ver como cada padrao responde a mesma requisicao.');
    container.appendChild(title);
    container.appendChild(desc);

    // Controls
    var controls = createElement('div', 'interactive-controls');
    var sendBtn = createElement('button', 'btn btn--primary', 'Enviar Request');
    var resetBtn = createElement('button', 'btn btn--ghost', 'Reset');
    resetBtn.style.display = 'none';
    controls.appendChild(sendBtn);
    controls.appendChild(resetBtn);
    container.appendChild(controls);

    // Grid
    var grid = createElement('div', 'pattern-grid');

    var cols = [
      { key: 'sync', label: 'Sync' },
      { key: 'stream', label: 'Stream' },
      { key: 'async', label: 'Async' },
    ];

    var colEls = {};

    cols.forEach(function (col) {
      var colEl = createElement('div', 'pattern-col pattern-col--' + col.key);

      var header = createElement('div', 'pattern-col-header');
      var labelSpan = document.createElement('span');
      labelSpan.textContent = col.label;
      var timerSpan = createElement('span', 'pattern-col-timer');
      timerSpan.textContent = '0.0s';
      header.appendChild(labelSpan);
      header.appendChild(timerSpan);

      var body = createElement('div', 'pattern-col-body');
      var idleMsg = createElement('span', 'waiting-msg');
      idleMsg.textContent = 'Aguardando...';
      body.appendChild(idleMsg);

      colEl.appendChild(header);
      colEl.appendChild(body);
      grid.appendChild(colEl);

      colEls[col.key] = { body: body, timer: timerSpan };
    });

    container.appendChild(grid);

    // State
    var running = false;
    var intervals = [];

    function clearAllIntervals() {
      intervals.forEach(function (id) { clearInterval(id); });
      intervals = [];
    }

    function startTimer(timerEl, startTime) {
      var id = setInterval(function () {
        var elapsed = (Date.now() - startTime) / 1000;
        timerEl.textContent = elapsed.toFixed(1) + 's';
      }, 100);
      intervals.push(id);
      return id;
    }

    function resetAll() {
      clearAllIntervals();
      running = false;
      sendBtn.disabled = false;
      sendBtn.style.display = '';
      resetBtn.style.display = 'none';

      cols.forEach(function (col) {
        var body = colEls[col.key].body;
        while (body.firstChild) body.removeChild(body.firstChild);
        var idle = createElement('span', 'waiting-msg');
        idle.textContent = 'Aguardando...';
        body.appendChild(idle);
        colEls[col.key].timer.textContent = '0.0s';
      });
    }

    // Helper to create a spinner element
    function createSpinner() {
      var wrapper = createElement('span', 'waiting-msg');
      var spinner = createElement('span', 'pattern-spinner');
      wrapper.appendChild(spinner);
      var text = document.createTextNode(' Processando...');
      wrapper.appendChild(text);
      return wrapper;
    }

    // --- Sync simulation ---
    function runSync(startTime) {
      var el = colEls.sync;
      while (el.body.firstChild) el.body.removeChild(el.body.firstChild);

      el.body.appendChild(createSpinner());

      var timerId = startTimer(el.timer, startTime);

      setTimeout(function () {
        clearInterval(timerId);
        el.timer.textContent = '5.0s';
        while (el.body.firstChild) el.body.removeChild(el.body.firstChild);

        var resultLine = createElement('span', 'result-msg');
        resultLine.textContent = '200 OK';
        el.body.appendChild(resultLine);

        el.body.appendChild(document.createElement('br'));

        var output = document.createElement('span');
        output.textContent = '{"output": "A resposta completa do agente aparece aqui de uma vez, apos todo o processamento ser concluido."}';
        el.body.appendChild(output);
      }, 5000);
    }

    // --- Stream simulation ---
    function runStream(startTime) {
      var el = colEls.stream;
      while (el.body.firstChild) el.body.removeChild(el.body.firstChild);

      var timerId = startTimer(el.timer, startTime);

      var events = [
        { delay: 300,  badge: 'step_start',  color: 'rgba(79,70,229,0.15)', textColor: '#818CF8', text: '{"step": 1, "type": "reasoning"}' },
        { delay: 800,  badge: 'tool_call',   color: 'rgba(234,88,12,0.15)',  textColor: '#fb923c', text: '{"tool": "search_database"}' },
        { delay: 2200, badge: 'tool_result', color: 'rgba(34,197,94,0.15)',  textColor: '#22c55e', text: '{"result": "3 registros"}' },
        { delay: 2600, badge: 'token',       color: 'rgba(148,163,184,0.1)', textColor: '#94a3b8', text: 'Encontrei ' },
        { delay: 2800, badge: 'token',       color: 'rgba(148,163,184,0.1)', textColor: '#94a3b8', text: '3 registros ' },
        { delay: 3000, badge: 'token',       color: 'rgba(148,163,184,0.1)', textColor: '#94a3b8', text: 'relevantes ' },
        { delay: 3200, badge: 'token',       color: 'rgba(148,163,184,0.1)', textColor: '#94a3b8', text: 'no banco ' },
        { delay: 3400, badge: 'token',       color: 'rgba(148,163,184,0.1)', textColor: '#94a3b8', text: 'de dados.' },
        { delay: 3800, badge: 'done',        color: 'rgba(79,70,229,0.2)',   textColor: '#818CF8', text: '{"total_tokens": 1847}' },
      ];

      var lastDelay = events[events.length - 1].delay;

      events.forEach(function (ev) {
        setTimeout(function () {
          var line = createElement('span', 'event-line');

          var badge = createElement('span', 'event-badge');
          badge.textContent = ev.badge;
          badge.style.backgroundColor = ev.color;
          badge.style.color = ev.textColor;

          var textSpan = document.createElement('span');
          textSpan.textContent = ev.text;
          if (ev.badge === 'token') {
            textSpan.style.color = 'var(--color-text)';
          } else {
            textSpan.style.color = 'var(--color-text-secondary)';
          }

          line.appendChild(badge);
          line.appendChild(textSpan);
          el.body.appendChild(line);

          // Auto-scroll
          el.body.scrollTop = el.body.scrollHeight;
        }, ev.delay);
      });

      setTimeout(function () {
        clearInterval(timerId);
      }, lastDelay);
    }

    // --- Async simulation with intermediate status updates ---
    function runAsync(startTime) {
      var el = colEls.async;
      while (el.body.firstChild) el.body.removeChild(el.body.firstChild);

      var timerId = startTimer(el.timer, startTime);

      // Immediate response
      setTimeout(function () {
        var immediate = createElement('span', 'result-msg');
        immediate.textContent = '202 Accepted';
        el.body.appendChild(immediate);

        el.body.appendChild(document.createElement('br'));

        var taskInfo = document.createElement('span');
        taskInfo.textContent = '{"task_id": "abc-123", "poll_url": "/tasks/abc-123"}';
        el.body.appendChild(taskInfo);

        el.body.appendChild(document.createElement('br'));
        el.body.appendChild(document.createElement('br'));

        var pollLabel = createElement('span', 'waiting-msg');
        pollLabel.textContent = 'Polling /tasks/abc-123...';
        el.body.appendChild(pollLabel);
      }, 200);

      // Status updates with intermediate messages
      var statusMessages = [
        { delay: 1500, text: 'Status: processing — Consultando base de dados...' },
        { delay: 3000, text: 'Status: processing — Gerando relatorio...' },
        { delay: 4500, text: 'Status: processing — Finalizando analise...' },
      ];

      statusMessages.forEach(function (msg) {
        setTimeout(function () {
          var statusLine = createElement('span', 'status-line status-line--active');
          statusLine.textContent = msg.text;
          el.body.appendChild(statusLine);
          el.body.scrollTop = el.body.scrollHeight;
        }, msg.delay);
      });

      // Final result
      setTimeout(function () {
        clearInterval(timerId);
        el.timer.textContent = '7.0s';

        el.body.appendChild(document.createElement('br'));

        var result = createElement('span', 'result-msg');
        result.textContent = 'Status: completed';
        el.body.appendChild(result);

        el.body.appendChild(document.createElement('br'));

        var data = document.createElement('span');
        data.textContent = '{"status": "completed", "result": "A resposta completa do agente, processada em background pelo worker."}';
        el.body.appendChild(data);

        el.body.scrollTop = el.body.scrollHeight;
      }, 7000);
    }

    // Event handlers
    sendBtn.addEventListener('click', function () {
      if (running) return;
      running = true;
      sendBtn.disabled = true;

      var startTime = Date.now();
      runSync(startTime);
      runStream(startTime);
      runAsync(startTime);

      // Show reset after longest completes
      setTimeout(function () {
        sendBtn.style.display = 'none';
        resetBtn.style.display = '';
      }, 7200);
    });

    resetBtn.addEventListener('click', resetAll);
  }

  // ============================================================
  // === 3. SSE Timeline ===
  // ============================================================

  function initSSETimeline() {
    var container = $('#sse-timeline');
    if (!container) return;

    var title = createElement('div', 'interactive-title', 'Timeline de Eventos SSE');
    var desc = createElement('div', 'interactive-description',
      'Eventos chegam sequencialmente conforme o agente processa. Observe o tipo, timestamp e payload de cada evento.');
    container.appendChild(title);
    container.appendChild(desc);

    // Controls
    var controls = createElement('div', 'interactive-controls');
    var replayBtn = createElement('button', 'btn btn--outline btn--sm', 'Replay');
    replayBtn.style.display = 'none';
    controls.appendChild(replayBtn);
    container.appendChild(controls);

    // Timeline container
    var timeline = createElement('div', 'sse-timeline');
    container.appendChild(timeline);

    // Mock events
    var mockEvents = [
      {
        type: 'step_start',
        time: '0.0s',
        delayMs: 0,
        data: '{"step": 1, "type": "reasoning"}',
      },
      {
        type: 'tool_call',
        time: '0.8s',
        delayMs: 800,
        data: '{"tool": "search_database", "args": {"query": "registros recentes"}}',
      },
      {
        type: 'tool_result',
        time: '2.1s',
        delayMs: 1300,
        data: '{"tool": "search_database", "result": "3 registros encontrados", "latency_ms": 1240}',
      },
      {
        type: 'token',
        time: '2.5s',
        delayMs: 400,
        data: '{"content": "Encontrei "}',
      },
      {
        type: 'token',
        time: '2.7s',
        delayMs: 200,
        data: '{"content": "3 registros "}',
      },
      {
        type: 'token',
        time: '2.9s',
        delayMs: 200,
        data: '{"content": "relevantes "}',
      },
      {
        type: 'token',
        time: '3.1s',
        delayMs: 200,
        data: '{"content": "no banco de dados."}',
      },
      {
        type: 'token',
        time: '3.3s',
        delayMs: 200,
        data: '{"content": " Os resultados mostram..."}',
      },
      {
        type: 'done',
        time: '3.8s',
        delayMs: 500,
        data: '{"total_tokens": 1847, "steps": 2, "tools_called": 1}',
      },
    ];

    var cardEls = [];
    var played = false;

    function buildCards() {
      while (timeline.firstChild) timeline.removeChild(timeline.firstChild);
      cardEls = [];

      mockEvents.forEach(function (ev) {
        var card = createElement('div', 'sse-event-card sse-event-card--' + ev.type);

        var header = createElement('div', 'sse-event-header');
        var typeBadge = createElement('span', 'sse-event-type sse-event-type--' + ev.type);
        typeBadge.textContent = ev.type;
        var timeStamp = createElement('span', 'sse-event-time');
        timeStamp.textContent = ev.time;
        header.appendChild(typeBadge);
        header.appendChild(timeStamp);

        var dataEl = createElement('div', 'sse-event-data');
        dataEl.textContent = 'data: ' + ev.data;

        card.appendChild(header);
        card.appendChild(dataEl);
        timeline.appendChild(card);
        cardEls.push(card);
      });
    }

    function playTimeline() {
      var cumulativeDelay = 0;

      mockEvents.forEach(function (ev, i) {
        cumulativeDelay += ev.delayMs;

        setTimeout(function () {
          if (cardEls[i]) {
            cardEls[i].classList.add('is-visible');
          }
        }, cumulativeDelay);
      });

      var totalDelay = 0;
      mockEvents.forEach(function (ev) { totalDelay += ev.delayMs; });

      setTimeout(function () {
        replayBtn.style.display = '';
      }, totalDelay + 500);
    }

    function replay() {
      replayBtn.style.display = 'none';
      buildCards();
      setTimeout(function () {
        playTimeline();
      }, 50);
    }

    // Build initial cards
    buildCards();

    // Auto-play on scroll
    onVisible(container, function () {
      if (!played) {
        played = true;
        playTimeline();
      }
    });

    replayBtn.addEventListener('click', function () {
      played = true;
      replay();
    });
  }

  // ============================================================
  // === Init ===
  // ============================================================

  document.addEventListener('DOMContentLoaded', function () {
    initPatternComparator();
    initSSETimeline();
  });
})();
