/**
 * chapter-03.js — Componentes interativos do Capítulo 03:
 * "Controles de Produção: Timeout, Concorrência e Resiliência"
 *
 * Três componentes:
 *   1. Simulador de Semáforo (semaphore-sim)
 *   2. Timeout em Cascata (timeout-cascade)
 *   3. Injetor de Falhas (fault-injector)
 */

'use strict';

(function () {
  var U = window.TextbookUtils;
  var createElement = U.createElement;
  var $ = U.$;
  var delay = U.delay;
  var debounce = U.debounce;

  // ============================================================
  // === 1. Simulador de Semáforo ===
  // ============================================================

  function initSemaphoreSimulator() {
    var container = $('#semaphore-sim');
    if (!container) return;

    // State
    var MAX_CONCURRENT = 3;
    var MAX_QUEUE = 10;
    var requests = [];
    var tickInterval = null;
    var running = false;
    var nextId = 1;

    // --- Build UI ---
    var title = createElement('div', 'interactive-title', 'Simulador de Semáforo');
    var desc = createElement('div', 'interactive-description',
      'Ajuste a concorrência máxima, o tamanho da fila, e envie um lote de requisições para observar como o semáforo distribui o tráfego.');
    container.appendChild(title);
    container.appendChild(desc);

    // Controls
    var controls = createElement('div', 'sem-controls');

    // Slider: MAX_CONCURRENT
    var concGroup = createElement('div', 'sem-control-group');
    var concLabel = createElement('label', 'form-label', 'MAX_CONCURRENT');
    var concRow = document.createElement('div');
    concRow.style.display = 'flex';
    concRow.style.alignItems = 'center';
    concRow.style.gap = 'var(--space-3)';
    var concSlider = document.createElement('input');
    concSlider.type = 'range';
    concSlider.className = 'slider';
    concSlider.min = '1';
    concSlider.max = '10';
    concSlider.value = '3';
    concSlider.setAttribute('aria-label', 'Concorrência máxima');
    var concVal = createElement('span', 'sem-slider-val', '3');
    concRow.appendChild(concSlider);
    concRow.appendChild(concVal);
    concGroup.appendChild(concLabel);
    concGroup.appendChild(concRow);

    // Slider: MAX_QUEUE
    var queueGroup = createElement('div', 'sem-control-group');
    var queueLabel = createElement('label', 'form-label', 'MAX_QUEUE');
    var queueRow = document.createElement('div');
    queueRow.style.display = 'flex';
    queueRow.style.alignItems = 'center';
    queueRow.style.gap = 'var(--space-3)';
    var queueSlider = document.createElement('input');
    queueSlider.type = 'range';
    queueSlider.className = 'slider';
    queueSlider.min = '1';
    queueSlider.max = '20';
    queueSlider.value = '10';
    queueSlider.setAttribute('aria-label', 'Tamanho máximo da fila');
    var queueVal = createElement('span', 'sem-slider-val', '10');
    queueRow.appendChild(queueSlider);
    queueRow.appendChild(queueVal);
    queueGroup.appendChild(queueLabel);
    queueGroup.appendChild(queueRow);

    // Send group
    var sendGroup = createElement('div', 'sem-send-group');
    var sendFormGroup = createElement('div', 'form-group');
    var sendLabel = createElement('label', 'form-label', 'Requests');
    var sendInput = document.createElement('input');
    sendInput.type = 'number';
    sendInput.className = 'number-input';
    sendInput.min = '1';
    sendInput.max = '30';
    sendInput.value = '8';
    sendInput.setAttribute('aria-label', 'Número de requests');
    sendFormGroup.appendChild(sendLabel);
    sendFormGroup.appendChild(sendInput);
    var sendBtn = createElement('button', 'btn btn--accent', 'Enviar');
    var resetBtn = createElement('button', 'btn btn--ghost btn--sm', 'Reset');

    sendGroup.appendChild(sendFormGroup);
    sendGroup.appendChild(sendBtn);
    sendGroup.appendChild(resetBtn);

    controls.appendChild(concGroup);
    controls.appendChild(queueGroup);
    controls.appendChild(sendGroup);
    container.appendChild(controls);

    // Stats
    var stats = createElement('div', 'sem-stats');
    var statActive = createStat('Ativas', '0', 'active');
    var statWaiting = createStat('Na fila', '0', 'waiting');
    var statCompleted = createStat('Completas', '0', 'completed');
    var statRejected = createStat('Rejeitadas', '0', 'rejected');
    stats.appendChild(statActive);
    stats.appendChild(statWaiting);
    stats.appendChild(statCompleted);
    stats.appendChild(statRejected);
    container.appendChild(stats);

    // Grid
    var grid = createElement('div', 'sem-grid');
    container.appendChild(grid);

    function createStat(label, value, type) {
      var stat = createElement('div', 'sem-stat');
      var lbl = createElement('div', 'sem-stat-label', label);
      var val = createElement('div', 'sem-stat-value sem-stat-value--' + type, value);
      val.setAttribute('data-stat', type);
      stat.appendChild(lbl);
      stat.appendChild(val);
      return stat;
    }

    function updateSliderProgress(slider) {
      var min = parseFloat(slider.min);
      var max = parseFloat(slider.max);
      var val = parseFloat(slider.value);
      var pct = ((val - min) / (max - min)) * 100;
      slider.style.setProperty('--slider-progress', pct + '%');
    }

    concSlider.addEventListener('input', function () {
      MAX_CONCURRENT = parseInt(concSlider.value, 10);
      concVal.textContent = String(MAX_CONCURRENT);
      updateSliderProgress(concSlider);
    });

    queueSlider.addEventListener('input', function () {
      MAX_QUEUE = parseInt(queueSlider.value, 10);
      queueVal.textContent = String(MAX_QUEUE);
      updateSliderProgress(queueSlider);
    });

    function updateStats() {
      var active = 0, waiting = 0, completed = 0, rejected = 0;
      for (var i = 0; i < requests.length; i++) {
        var s = requests[i].state;
        if (s === 'active') active++;
        else if (s === 'waiting') waiting++;
        else if (s === 'completed') completed++;
        else if (s === 'rejected') rejected++;
      }
      var sa = $('[data-stat="active"]', container);
      var sw = $('[data-stat="waiting"]', container);
      var sc = $('[data-stat="completed"]', container);
      var sr = $('[data-stat="rejected"]', container);
      if (sa) sa.textContent = String(active);
      if (sw) sw.textContent = String(waiting);
      if (sc) sc.textContent = String(completed);
      if (sr) sr.textContent = String(rejected);
    }

    function createCircle(req) {
      var circle = document.createElement('div');
      circle.className = 'sem-circle sem-circle--idle';
      circle.setAttribute('data-id', req.id);
      circle.setAttribute('data-req-id', req.id);
      return circle;
    }

    function updateCircle(req) {
      var circle = $('[data-req-id="' + req.id + '"]', grid);
      if (!circle) return;
      circle.className = 'sem-circle sem-circle--' + req.state;
    }

    function resetSimulation() {
      if (tickInterval) {
        clearInterval(tickInterval);
        tickInterval = null;
      }
      running = false;
      requests = [];
      nextId = 1;
      grid.textContent = '';
      updateStats();
      sendBtn.disabled = false;
    }

    function startSimulation(count) {
      if (running) return;
      running = true;
      sendBtn.disabled = true;

      var activeCount = 0;
      var waitingCount = 0;

      // Create all requests
      for (var i = 0; i < count; i++) {
        var req = { id: nextId++, state: 'idle' };
        requests.push(req);
        var circle = createCircle(req);
        grid.appendChild(circle);
      }

      // Classify: active, waiting, or rejected
      for (var i = 0; i < requests.length; i++) {
        var req = requests[i];
        if (req.state !== 'idle') continue;

        if (activeCount < MAX_CONCURRENT) {
          req.state = 'active';
          activeCount++;
        } else if (waitingCount < MAX_QUEUE) {
          req.state = 'waiting';
          waitingCount++;
        } else {
          req.state = 'rejected';
        }
        updateCircle(req);
      }

      updateStats();

      // Tick: every 1.5s, complete one active, promote one waiting
      tickInterval = setInterval(function () {
        // Find first active and complete it
        var completedOne = false;
        for (var i = 0; i < requests.length; i++) {
          if (requests[i].state === 'active') {
            requests[i].state = 'completed';
            updateCircle(requests[i]);
            completedOne = true;
            break;
          }
        }

        // Promote first waiting to active
        if (completedOne) {
          for (var i = 0; i < requests.length; i++) {
            if (requests[i].state === 'waiting') {
              requests[i].state = 'active';
              updateCircle(requests[i]);
              break;
            }
          }
        }

        updateStats();

        // Check if done
        var allDone = true;
        for (var i = 0; i < requests.length; i++) {
          if (requests[i].state === 'active' || requests[i].state === 'waiting') {
            allDone = false;
            break;
          }
        }

        if (allDone) {
          clearInterval(tickInterval);
          tickInterval = null;
          running = false;
          sendBtn.disabled = false;
        }
      }, 1500);
    }

    sendBtn.addEventListener('click', function () {
      var count = parseInt(sendInput.value, 10);
      if (isNaN(count) || count < 1) count = 1;
      if (count > 30) count = 30;
      // Reset before new batch
      resetSimulation();
      // Small delay só reset visually completes
      setTimeout(function () {
        startSimulation(count);
      }, 50);
    });

    resetBtn.addEventListener('click', function () {
      resetSimulation();
    });

    // Initialize slider progress
    updateSliderProgress(concSlider);
    updateSliderProgress(queueSlider);
  }

  // ============================================================
  // === 2. Timeout em Cascata ===
  // ============================================================

  function initTimeoutCascade() {
    var container = $('#timeout-cascade');
    if (!container) return;

    // Default timeouts
    var timeoutRequest = 120;
    var timeoutAgent = 90;
    var timeoutTool = 30;
    var slowTool = false;
    var complexAgent = false;
    var animating = false;
    var animationId = null;

    // Build UI
    var title = createElement('div', 'interactive-title', 'Timeout em Cascata');
    var desc = createElement('div', 'interactive-description',
      'Ajuste os timeouts de cada camada e ative cenários de falha para ver como os erros se propagam.');
    container.appendChild(title);
    container.appendChild(desc);

    // Controls grid
    var controls = createElement('div', 'tc-controls');

    // Timeout sliders
    var sliders = [
      { label: 'Request timeout (s)', min: 30, max: 180, val: 120, id: 'request' },
      { label: 'Agent timeout (s)', min: 10, max: 150, val: 90, id: 'agent' },
      { label: 'Tool timeout (s)', min: 5, max: 60, val: 30, id: 'tool' },
    ];

    var sliderEls = {};

    sliders.forEach(function (cfg) {
      var group = createElement('div', 'form-group');
      var label = createElement('label', 'form-label', cfg.label);
      var row = document.createElement('div');
      row.style.display = 'flex';
      row.style.alignItems = 'center';
      row.style.gap = 'var(--space-3)';
      var slider = document.createElement('input');
      slider.type = 'range';
      slider.className = 'slider';
      slider.min = String(cfg.min);
      slider.max = String(cfg.max);
      slider.value = String(cfg.val);
      slider.setAttribute('aria-label', cfg.label);
      var val = createElement('span', 'sem-slider-val', String(cfg.val));
      row.appendChild(slider);
      row.appendChild(val);
      group.appendChild(label);
      group.appendChild(row);
      controls.appendChild(group);

      sliderEls[cfg.id] = { slider: slider, display: val };

      slider.addEventListener('input', function () {
        var v = parseInt(slider.value, 10);
        val.textContent = String(v);
        if (cfg.id === 'request') timeoutRequest = v;
        else if (cfg.id === 'agent') timeoutAgent = v;
        else if (cfg.id === 'tool') timeoutTool = v;
        var pct = ((v - cfg.min) / (cfg.max - cfg.min)) * 100;
        slider.style.setProperty('--slider-progress', pct + '%');
      });

      // Init slider progress
      var pct = ((cfg.val - cfg.min) / (cfg.max - cfg.min)) * 100;
      slider.style.setProperty('--slider-progress', pct + '%');
    });

    container.appendChild(controls);

    // Toggles + button row
    var toggleRow = document.createElement('div');
    toggleRow.style.display = 'flex';
    toggleRow.style.flexWrap = 'wrap';
    toggleRow.style.gap = 'var(--space-6)';
    toggleRow.style.alignItems = 'center';
    toggleRow.style.marginBottom = 'var(--space-6)';

    // Toggle: Tool lenta
    var toggleToolWrap = createElement('div', 'tc-toggle-row');
    var toggleToolBtn = document.createElement('button');
    toggleToolBtn.className = 'tc-toggle';
    toggleToolBtn.setAttribute('aria-label', 'Tool lenta');
    toggleToolBtn.setAttribute('role', 'switch');
    toggleToolBtn.setAttribute('aria-checked', 'false');
    var toggleToolLabel = createElement('span', 'tc-toggle-label', 'Tool lenta');
    toggleToolWrap.appendChild(toggleToolBtn);
    toggleToolWrap.appendChild(toggleToolLabel);

    // Toggle: Agente complexo
    var toggleAgentWrap = createElement('div', 'tc-toggle-row');
    var toggleAgentBtn = document.createElement('button');
    toggleAgentBtn.className = 'tc-toggle';
    toggleAgentBtn.setAttribute('aria-label', 'Agente complexo');
    toggleAgentBtn.setAttribute('role', 'switch');
    toggleAgentBtn.setAttribute('aria-checked', 'false');
    var toggleAgentLabel = createElement('span', 'tc-toggle-label', 'Agente complexo');
    toggleAgentWrap.appendChild(toggleAgentBtn);
    toggleAgentWrap.appendChild(toggleAgentLabel);

    var simBtn = createElement('button', 'btn btn--accent', 'Simular');

    toggleRow.appendChild(toggleToolWrap);
    toggleRow.appendChild(toggleAgentWrap);
    toggleRow.appendChild(simBtn);
    container.appendChild(toggleRow);

    toggleToolBtn.addEventListener('click', function () {
      slowTool = !slowTool;
      toggleToolBtn.classList.toggle('is-on', slowTool);
      toggleToolBtn.setAttribute('aria-checked', String(slowTool));
    });

    toggleAgentBtn.addEventListener('click', function () {
      complexAgent = !complexAgent;
      toggleAgentBtn.classList.toggle('is-on', complexAgent);
      toggleAgentBtn.setAttribute('aria-checked', String(complexAgent));
    });

    // Nested boxes
    var boxes = createElement('div', 'tc-boxes');

    var outerBox = createElement('div', 'tc-box tc-box--outer');
    var outerHeader = createElement('div', 'tc-box-header');
    var outerLabel = createElement('span', 'tc-box-label', 'Request');
    var outerTimer = createElement('span', 'tc-timer', '0.0s');
    outerHeader.appendChild(outerLabel);
    outerHeader.appendChild(outerTimer);
    var outerProgress = createElement('div', 'tc-progress');
    var outerFill = createElement('div', 'tc-progress-fill');
    outerProgress.appendChild(outerFill);
    outerBox.appendChild(outerHeader);
    outerBox.appendChild(outerProgress);

    var middleBox = createElement('div', 'tc-box tc-box--middle');
    var middleHeader = createElement('div', 'tc-box-header');
    var middleLabel = createElement('span', 'tc-box-label', 'Agente');
    var middleTimer = createElement('span', 'tc-timer', '0.0s');
    middleHeader.appendChild(middleLabel);
    middleHeader.appendChild(middleTimer);
    var middleProgress = createElement('div', 'tc-progress');
    var middleFill = createElement('div', 'tc-progress-fill');
    middleProgress.appendChild(middleFill);
    middleBox.appendChild(middleHeader);
    middleBox.appendChild(middleProgress);

    var innerBox = createElement('div', 'tc-box tc-box--inner');
    var innerHeader = createElement('div', 'tc-box-header');
    var innerLabel = createElement('span', 'tc-box-label', 'Tool');
    var innerTimer = createElement('span', 'tc-timer', '0.0s');
    innerHeader.appendChild(innerLabel);
    innerHeader.appendChild(innerTimer);
    var innerProgress = createElement('div', 'tc-progress');
    var innerFill = createElement('div', 'tc-progress-fill');
    innerProgress.appendChild(innerFill);
    innerBox.appendChild(innerHeader);
    innerBox.appendChild(innerProgress);

    middleBox.appendChild(innerBox);
    outerBox.appendChild(middleBox);
    boxes.appendChild(outerBox);
    container.appendChild(boxes);

    // Result area
    var result = document.createElement('div');
    result.className = 'tc-result';
    result.setAttribute('id', 'tc-result');
    container.appendChild(result);

    function setTimerClass(timerEl, pct) {
      timerEl.className = 'tc-timer';
      if (pct >= 1.0) {
        timerEl.classList.add('tc-timer--red');
      } else if (pct >= 0.8) {
        timerEl.classList.add('tc-timer--yellow');
      } else {
        timerEl.classList.add('tc-timer--green');
      }
    }

    function setFillColor(fillEl, pct) {
      if (pct >= 1.0) {
        fillEl.style.backgroundColor = 'var(--color-error)';
      } else if (pct >= 0.8) {
        fillEl.style.backgroundColor = 'var(--color-warning)';
      } else {
        fillEl.style.backgroundColor = 'var(--color-success)';
      }
    }

    function resetBoxes() {
      [outerTimer, middleTimer, innerTimer].forEach(function (t) {
        t.textContent = '0.0s';
        t.className = 'tc-timer';
      });
      [outerFill, middleFill, innerFill].forEach(function (f) {
        f.style.width = '0%';
        f.style.backgroundColor = 'var(--color-success)';
      });
      [outerBox, middleBox, innerBox].forEach(function (b) {
        b.style.borderColor = '';
      });
      result.className = 'tc-result';
      result.textContent = '';
    }

    function runSimulation() {
      if (animating) return;
      animating = true;
      simBtn.disabled = true;
      resetBoxes();

      // Determine durations (in simulated seconds — we speed up by 20x)
      var speedFactor = 20;
      // Normal: tool takes 60% of its timeout, agent takes 60% of its timeout
      var toolDuration = slowTool ? (timeoutTool * 1.3) : (timeoutTool * 0.6);
      var agentDuration = complexAgent ? (timeoutAgent * 1.2) : (timeoutAgent * 0.6);

      // If tool is slow, agent duration includes tool duration
      var effectiveAgentDuration = Math.max(agentDuration, toolDuration + 5);
      // Request duration wraps everything
      var effectiveRequestDuration = effectiveAgentDuration + 3;

      // Detect failure point
      var toolFailed = slowTool && toolDuration > timeoutTool;
      var agentFailed = !toolFailed && complexAgent && effectiveAgentDuration > timeoutAgent;

      // Cap durations at timeout when failure occurs
      var toolDisplay = toolFailed ? timeoutTool : Math.min(toolDuration, timeoutTool);
      var agentDisplay = toolFailed ? (toolDisplay + 2) : (agentFailed ? timeoutAgent : Math.min(effectiveAgentDuration, timeoutAgent));
      var requestDisplay = toolFailed ? (agentDisplay + 2) : (agentFailed ? (agentDisplay + 2) : Math.min(effectiveRequestDuration, timeoutRequest));

      var startTime = performance.now();

      function tick(now) {
        var elapsed = (now - startTime) / 1000; // real seconds elapsed
        var simElapsed = elapsed * speedFactor; // simulated seconds

        // Tool timer
        var toolElapsed = Math.min(simElapsed, toolDisplay);
        var toolPct = toolElapsed / timeoutTool;
        innerTimer.textContent = toolElapsed.toFixed(1) + 's';
        innerFill.style.width = Math.min(toolPct * 100, 100) + '%';
        setTimerClass(innerTimer, toolPct);
        setFillColor(innerFill, toolPct);

        // Agent timer
        var agentElapsed = Math.min(simElapsed, agentDisplay);
        var agentPct = agentElapsed / timeoutAgent;
        middleTimer.textContent = agentElapsed.toFixed(1) + 's';
        middleFill.style.width = Math.min(agentPct * 100, 100) + '%';
        setTimerClass(middleTimer, agentPct);
        setFillColor(middleFill, agentPct);

        // Request timer
        var reqElapsed = Math.min(simElapsed, requestDisplay);
        var reqPct = reqElapsed / timeoutRequest;
        outerTimer.textContent = reqElapsed.toFixed(1) + 's';
        outerFill.style.width = Math.min(reqPct * 100, 100) + '%';
        setTimerClass(outerTimer, reqPct);
        setFillColor(outerFill, reqPct);

        if (simElapsed < requestDisplay) {
          animationId = requestAnimationFrame(tick);
        } else {
          // Show result
          if (toolFailed) {
            innerBox.style.borderColor = 'var(--color-error)';
            middleBox.style.borderColor = 'var(--color-error)';
            outerBox.style.borderColor = 'var(--color-error)';
            result.className = 'tc-result tc-result--error';
            result.textContent = 'ToolExecutionError: Tool excedeu o timeout de ' + timeoutTool + 's \u2192 AgentTimeoutError propagado \u2192 504 Gateway Timeout';
          } else if (agentFailed) {
            middleBox.style.borderColor = 'var(--color-error)';
            outerBox.style.borderColor = 'var(--color-error)';
            result.className = 'tc-result tc-result--error';
            result.textContent = 'AgentTimeoutError: Agente excedeu o timeout de ' + timeoutAgent + 's \u2192 504 Gateway Timeout';
          } else {
            innerBox.style.borderColor = 'var(--color-success)';
            middleBox.style.borderColor = 'var(--color-success)';
            outerBox.style.borderColor = 'var(--color-success)';
            result.className = 'tc-result tc-result--success';
            result.textContent = 'Sucesso: todas as camadas completaram dentro dos limites de timeout.';
          }
          animating = false;
          simBtn.disabled = false;
        }
      }

      animationId = requestAnimationFrame(tick);
    }

    simBtn.addEventListener('click', function () {
      if (animating && animationId) {
        cancelAnimationFrame(animationId);
        animating = false;
        simBtn.disabled = false;
      }
      runSimulation();
    });
  }

  // ============================================================
  // === 3. Injetor de Falhas ===
  // ============================================================

  function initFaultInjector() {
    var container = $('#fault-injector');
    if (!container) return;

    var animating = false;

    // Fault definitions
    var FAULTS = {
      timeout: {
        label: 'Timeout do Agente',
        faultNode: 2, // agent node
        httpStatus: '504',
        httpText: 'Gateway Timeout',
        errorClass: 'AgentTimeoutError',
        detail: 'O agente excedeu o tempo limite de 90 segundos.',
      },
      concurrency: {
        label: 'Limite de Concorrência',
        faultNode: 1, // semaphore node
        httpStatus: '429',
        httpText: 'Too Many Requests',
        errorClass: 'ConcurrencyLimitError',
        detail: 'Fila de concorrência cheia: 10/10 slots ocupados.',
      },
      tool: {
        label: 'Falha na Tool',
        faultNode: 3, // tool node
        httpStatus: '502',
        httpText: 'Bad Gateway',
        errorClass: 'ToolExecutionError',
        detail: 'Tool "search_database" falhou: ConnectionTimeout após 30s.',
      },
    };

    // Build UI
    var title = createElement('div', 'interactive-title', 'Injetor de Falhas');
    var desc = createElement('div', 'interactive-description',
      'Selecione um tipo de erro é observe como a falha se propaga pela stack, desde o ponto de origem até a resposta HTTP.');
    container.appendChild(title);
    container.appendChild(desc);

    // Controls
    var controlsDiv = createElement('div', 'fi-controls');

    var selectGroup = createElement('div', 'form-group');
    var selectLabel = createElement('label', 'form-label', 'Tipo de erro');
    var select = document.createElement('select');
    select.className = 'select';
    select.setAttribute('aria-label', 'Tipo de erro');

    Object.keys(FAULTS).forEach(function (key) {
      var opt = document.createElement('option');
      opt.value = key;
      opt.textContent = FAULTS[key].label;
      select.appendChild(opt);
    });

    selectGroup.appendChild(selectLabel);
    selectGroup.appendChild(select);
    controlsDiv.appendChild(selectGroup);

    var injectBtn = createElement('button', 'btn btn--accent', 'Injetar Falha');
    controlsDiv.appendChild(injectBtn);
    container.appendChild(controlsDiv);

    // Flow visualization
    var NODE_LABELS = ['Request', 'Semáforo', 'Agente', 'Tool', 'Resposta'];

    var flow = createElement('div', 'fi-flow');
    var nodeEls = [];
    var arrowEls = [];

    NODE_LABELS.forEach(function (label, idx) {
      var nodeEl = document.createElement('div');
      nodeEl.className = 'fi-node';
      nodeEl.textContent = label;
      flow.appendChild(nodeEl);
      nodeEls.push(nodeEl);

      if (idx < NODE_LABELS.length - 1) {
        var arrow = document.createElement('span');
        arrow.className = 'fi-arrow';
        arrow.textContent = '\u2192';
        flow.appendChild(arrow);
        arrowEls.push(arrow);
      }
    });

    container.appendChild(flow);

    // Response panel
    var responseLabel = createElement('div', 'form-label', 'Resposta HTTP');
    responseLabel.style.marginBottom = 'var(--space-2)';
    container.appendChild(responseLabel);

    var responsePanel = document.createElement('div');
    responsePanel.className = 'fi-response';
    responsePanel.textContent = 'Clique em "Injetar Falha" para iniciar a simulacao.';
    container.appendChild(responsePanel);

    function resetFlow() {
      flow.querySelectorAll('.fi-dot').forEach(function(d) { d.remove(); });
      nodeEls.forEach(function (el, idx) {
        el.className = 'fi-node';
        el.textContent = NODE_LABELS[idx];
      });
      arrowEls.forEach(function (el) {
        el.className = 'fi-arrow';
      });
      responsePanel.className = 'fi-response';
      responsePanel.textContent = '';
    }

    async function runFaultAnimation(faultKey) {
      if (animating) return;
      animating = true;
      injectBtn.disabled = true;
      resetFlow();

      var animate = Motion.animate;
      var fault = FAULTS[faultKey];
      var faultNodeIdx = fault.faultNode;

      // Helper: get node center relative to flow container
      function getCenter(node) {
        var nr = node.getBoundingClientRect();
        var fr = flow.getBoundingClientRect();
        return { x: nr.left - fr.left + nr.width / 2 + flow.scrollLeft, y: nr.top - fr.top + nr.height / 2 + flow.scrollTop };
      }

      // Helper: create a dot
      function createDot(color) {
        var dot = document.createElement('div');
        dot.className = 'fi-dot';
        dot.style.color = color;
        dot.style.backgroundColor = color;
        dot.style.opacity = '0';
        flow.appendChild(dot);
        return dot;
      }

      // Phase 1: Green dot travels from Request through nodes toward fault point
      var startPos = getCenter(nodeEls[0]);
      var requestDot = createDot('#22c55e');
      requestDot.style.left = startPos.x + 'px';
      requestDot.style.top = startPos.y + 'px';

      await animate(requestDot, { opacity: 1 }, { duration: 0.08 });

      for (var i = 0; i <= Math.min(faultNodeIdx, NODE_LABELS.length - 1); i++) {
        var pos = getCenter(nodeEls[i]);
        await animate(requestDot, { left: pos.x + 'px', top: pos.y + 'px' }, { duration: 0.4, easing: 'ease-in-out' });
        nodeEls[i].className = 'fi-node fi-node--active';
        if (i > 0) arrowEls[i - 1].className = 'fi-arrow fi-arrow--active';
      }

      // Phase 2: Dot arrives at fault node — turns red, node goes fault
      await new Promise(function(r) { setTimeout(r, 300); });
      requestDot.style.backgroundColor = '#ef4444';
      requestDot.style.color = '#ef4444';
      nodeEls[faultNodeIdx].className = 'fi-node fi-node--fault';
      await animate(requestDot, { opacity: 0 }, { duration: 0.3 });
      requestDot.remove();

      // Phase 3: Red error dot propagates back from fault node to Request
      await new Promise(function(r) { setTimeout(r, 200); });

      var faultPos = getCenter(nodeEls[faultNodeIdx]);
      var errorDot = createDot('#ef4444');
      errorDot.style.left = faultPos.x + 'px';
      errorDot.style.top = faultPos.y + 'px';

      await animate(errorDot, { opacity: 1 }, { duration: 0.08 });

      for (var i = faultNodeIdx - 1; i >= 0; i--) {
        var pos = getCenter(nodeEls[i]);
        arrowEls[i].className = 'fi-arrow fi-arrow--error';
        await animate(errorDot, { left: pos.x + 'px', top: pos.y + 'px' }, { duration: 0.3, easing: 'ease-in-out' });
        nodeEls[i].className = 'fi-node fi-node--propagate';
      }

      // Phase 4: Error dot reaches Response node
      var respIdx = NODE_LABELS.length - 1;
      for (var a = faultNodeIdx; a < respIdx; a++) {
        if (arrowEls[a]) arrowEls[a].className = 'fi-arrow fi-arrow--error';
      }
      var respPos = getCenter(nodeEls[respIdx]);
      await animate(errorDot, { left: respPos.x + 'px', top: respPos.y + 'px' }, { duration: 0.3, easing: 'ease-in-out' });
      nodeEls[respIdx].className = 'fi-node fi-node--fault';
      nodeEls[respIdx].textContent = fault.httpStatus;

      await animate(errorDot, { opacity: 0 }, { duration: 0.2 });
      errorDot.remove();

      // Phase 5: Show JSON response
      responsePanel.className = 'fi-response fi-response--error';
      var jsonResponse = JSON.stringify({
        error: fault.errorClass,
        detail: fault.detail,
        status: parseInt(fault.httpStatus, 10),
      }, null, 2);
      responsePanel.textContent = 'HTTP ' + fault.httpStatus + ' ' + fault.httpText + '\n\n' + jsonResponse;

      animating = false;
      injectBtn.disabled = false;
    }

    injectBtn.addEventListener('click', function () {
      var faultKey = select.value;
      runFaultAnimation(faultKey);
    });
  }

  // ============================================================
  // === Inicialização ===
  // ============================================================

  document.addEventListener('DOMContentLoaded', function () {
    initSemaphoreSimulator();
    initTimeoutCascade();
    initFaultInjector();
  });
})();
