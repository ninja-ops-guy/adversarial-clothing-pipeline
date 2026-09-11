(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  let runtimeConnected = false;
  let activeRunId = null;
  let pollTimer = null;
  let validationPassedFor = null;
  let analysisPassedFor = null;

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const cell = (label, value) => `
    <div class="status-item">
      <small>${escapeHtml(label)}</small>
      <b>${escapeHtml(value)}</b>
    </div>`;

  async function loadStatus() {
    const target = $('experimentStatus');
    if (!target) return;
    try {
      const response = await fetch('../d2-latest-status.json', { cache: 'no-store' });
      if (response.status === 404) {
        target.innerHTML = '<div class="loading">No closed generation is currently published.</div>';
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const status = await response.json();
      const generation = status.candidate_id || status.generation_id || 'Unknown';
      const decision = status.decision || status.outcome || 'Unknown';
      const evidence = status.evidence_state || 'Unknown';
      const closedDate = status.closed_date || status.closed_utc || status.closed_at || 'Not recorded in d2-latest-status.json';
      const sourceCommit = status.source_commit ? status.source_commit.slice(0, 12) : 'Not recorded';
      target.innerHTML = `<div class="status-grid">
        ${cell('Generation', generation)}
        ${cell('Outcome', decision)}
        ${cell('Evidence state', evidence)}
        ${cell('Closed date', closedDate)}
        ${cell('Bundle verified', status.bundle_verified === true ? 'YES' : status.bundle_verified === false ? 'NO' : 'Not recorded')}
        ${cell('Source commit', sourceCommit)}
      </div>`;
    } catch (error) {
      console.error('Research Console status load failed:', error);
      target.innerHTML = `<div class="error">Experiment status unavailable (${escapeHtml(error.message)}). No state was fabricated.</div>`;
    }
  }

  function sessionPath() { return $('sessionPath')?.value.trim() || ''; }
  function inferencePath() { return $('inferencePath')?.value.trim() || ''; }

  function resetWorkflowGate() {
    validationPassedFor = null;
    analysisPassedFor = null;
    updateWorkflowControls();
  }

  function updateWorkflowControls() {
    if (!$('validateSessionBtn')) return;
    const session = sessionPath();
    const inference = inferencePath();
    $('validateSessionBtn').disabled = !runtimeConnected || !session;
    $('analyzeSessionBtn').disabled = !runtimeConnected || !session || validationPassedFor !== session;
    $('ingestSessionBtn').disabled = !runtimeConnected || !session || !inference || validationPassedFor !== session || analysisPassedFor !== inference;
  }

  function setRuntimeControls(enabled) {
    document.querySelectorAll('[data-job], #stageSessionBtn, #refreshWorkspaceBtn')
      .forEach((node) => { node.disabled = !enabled; });
    updateWorkflowControls();
  }

  async function checkRuntime() {
    const light = $('runtimeLight');
    const title = $('runtimeTitle');
    const detail = $('runtimeDetail');
    try {
      const response = await fetch('/api/runtime/status', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const status = await response.json();
      runtimeConnected = status.connected === true;
      if (!runtimeConnected) throw new Error('runtime did not report connected');
      light.classList.add('connected');
      title.textContent = 'LOCAL RESEARCH RUNTIME CONNECTED';
      detail.textContent = `Python ${status.python} · workspace ${status.workspace} · ${status.running} active job(s)`;
      restoreLastSession();
      setRuntimeControls(true);
      await loadWorkspace();
    } catch (error) {
      runtimeConnected = false;
      light.classList.remove('connected');
      title.textContent = 'STATIC / READ-ONLY MODE';
      detail.innerHTML = 'Open this page through <code>rac-platform</code> or <code>run-rac-platform.bat</code> to execute research locally. GitHub Pages cannot safely run the Python/FFmpeg/model stack.';
      setRuntimeControls(false);
      if ($('workspaceFiles')) $('workspaceFiles').innerHTML = '<span class="muted">No local runtime connected.</span>';
    }
  }

  async function runtimeJson(path, options = {}) {
    if (!runtimeConnected) throw new Error('local research runtime is not connected');
    const response = await fetch(path, { cache: 'no-store', ...options });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  function normalizeUploadPath(path) {
    return String(path || '').replaceAll('\\', '/').split('/').filter(Boolean).map(encodeURIComponent).join('/');
  }

  function workspaceFileUrl(path) {
    return `/api/runtime/workspace/${normalizeUploadPath(path)}`;
  }

  function humanBytes(bytes) {
    const value = Number(bytes || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
    if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
    return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GiB`;
  }

  async function loadWorkspace() {
    const target = $('workspaceFiles');
    if (!target) return;
    if (!runtimeConnected) {
      target.innerHTML = '<span class="muted">No local runtime connected.</span>';
      return;
    }
    try {
      const payload = await runtimeJson('/api/runtime/workspace');
      const files = [...(payload.files || [])]
        .sort((a, b) => Number(b.modified || 0) - Number(a.modified || 0))
        .slice(0, 200);
      if (!files.length) {
        target.innerHTML = '<span class="muted">Local workspace is empty.</span>';
        return;
      }
      target.innerHTML = files.map((file) => {
        const safePath = escapeHtml(file.path);
        const when = file.modified ? new Date(file.modified * 1000).toLocaleString() : 'unknown time';
        return `<div class="workspace-file">
          <a href="${workspaceFileUrl(file.path)}" target="_blank" rel="noopener">${safePath}</a>
          <small>${escapeHtml(humanBytes(file.bytes))} · ${escapeHtml(when)}</small>
        </div>`;
      }).join('');
    } catch (error) {
      target.innerHTML = `<span class="error">Workspace listing failed: ${escapeHtml(error.message)}</span>`;
    }
  }

  function renderRun(run) {
    activeRunId = run.run_id;
    $('runSummary').textContent = `${run.title || run.job_id} · ${String(run.status).toUpperCase()} · ${run.run_id}`;
    $('runSummary').className = `inline-status run-${run.status}`;
    $('runLog').textContent = (run.log_tail || []).join('\n') || 'Job launched. Waiting for output…';
    if (['queued', 'running'].includes(run.status)) {
      clearTimeout(pollTimer);
      pollTimer = setTimeout(() => pollRun(run.run_id), 1200);
    } else if (run.status === 'succeeded') {
      loadWorkspace();
    }
  }

  async function pollRun(runId) {
    if (!runId || runId !== activeRunId) return;
    try {
      const run = await runtimeJson(`/api/runtime/runs/${encodeURIComponent(runId)}`);
      renderRun(run);
    } catch (error) {
      $('runSummary').textContent = `Runtime polling error: ${error.message}`;
      $('runSummary').className = 'inline-status run-failed';
    }
  }

  async function runJob(jobId, params = {}) {
    try {
      $('runSummary').textContent = `Launching ${jobId}…`;
      const run = await runtimeJson('/api/runtime/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, params }),
      });
      renderRun(run);
      return run;
    } catch (error) {
      $('runSummary').textContent = `${jobId} refused: ${error.message}`;
      $('runSummary').className = 'inline-status run-failed';
      $('runLog').textContent = String(error.stack || error);
      throw error;
    }
  }

  async function runJobAndWait(jobId, params = {}) {
    const launched = await runJob(jobId, params);
    let current = launched;
    while (['queued', 'running'].includes(current.status)) {
      await new Promise((resolve) => setTimeout(resolve, 900));
      current = await runtimeJson(`/api/runtime/runs/${encodeURIComponent(launched.run_id)}`);
      renderRun(current);
    }
    return current;
  }

  async function uploadWorkspaceFile(relPath, blob) {
    const safeUrlPath = normalizeUploadPath(relPath);
    return runtimeJson(`/api/runtime/workspace/${safeUrlPath}`, { method: 'PUT', body: blob });
  }

  async function stageSelectedSession() {
    const input = $('sessionFolder');
    const files = [...(input.files || [])];
    if (!files.length) {
      $('stageStatus').textContent = 'Choose a sealed Capture Lab folder first.';
      return;
    }
    const root = `imports/${new Date().toISOString().replaceAll(':', '').replaceAll('.', '-')}`;
    let sessionRel = null;
    $('stageStatus').textContent = `Staging ${files.length} file(s)…`;
    let completed = 0;
    for (const file of files) {
      const inside = file.webkitRelativePath || file.name;
      const rel = `${root}/${inside}`;
      await uploadWorkspaceFile(rel, file);
      completed += 1;
      $('stageStatus').textContent = `Staging ${completed}/${files.length}: ${inside}`;
      if (file.name.endsWith('-session.json') || file.name === 'session.json') sessionRel = rel;
    }
    if (!sessionRel) {
      $('stageStatus').textContent = 'Files staged, but no *-session.json was found.';
      await loadWorkspace();
      return;
    }
    const base = sessionRel.slice(0, sessionRel.lastIndexOf('/') + 1);
    $('sessionPath').value = sessionRel;
    $('inferencePath').value = `${base}inference.json`;
    $('p1OutputDir').value = `${base}p1-output`;
    $('trialStorePath').value = 'research/p1/trials.jsonl';
    resetWorkflowGate();
    rememberSession();
    $('stageStatus').textContent = `STAGED · ${sessionRel} · VALIDATION REQUIRED`;
    await loadWorkspace();
  }

  function sessionParams() {
    return {
      session: sessionPath(),
      inference: inferencePath(),
      output_dir: $('p1OutputDir').value.trim(),
      trial_store: $('trialStorePath').value.trim(),
    };
  }

  function rememberSession() {
    const state = sessionParams();
    try { localStorage.setItem('racLastStagedSession', JSON.stringify(state)); } catch (_) { /* non-critical */ }
  }

  function restoreLastSession() {
    try {
      const raw = localStorage.getItem('racLastStagedSession');
      if (!raw) return;
      const state = JSON.parse(raw);
      if (state.session && !$('sessionPath').value) $('sessionPath').value = state.session;
      if (state.inference && !$('inferencePath').value) $('inferencePath').value = state.inference;
      if (state.output_dir && !$('p1OutputDir').value) $('p1OutputDir').value = state.output_dir;
      if (state.trial_store && !$('trialStorePath').value) $('trialStorePath').value = state.trial_store;
      if (state.session) $('stageStatus').textContent = `LAST STAGED · ${state.session} · VALIDATION REQUIRED`;
    } catch (_) { /* ignore stale local UI state */ }
  }

  async function validateCurrentSession() {
    rememberSession();
    const session = sessionPath();
    validationPassedFor = null;
    analysisPassedFor = null;
    updateWorkflowControls();
    const run = await runJobAndWait('validate_capture', { session });
    if (run.status === 'succeeded') {
      validationPassedFor = session;
      $('stageStatus').textContent = `VALIDATED · ${session} · calibration/schedule/hashes PASS`;
    } else {
      $('stageStatus').textContent = `VALIDATION FAILED · ${session}`;
    }
    updateWorkflowControls();
    return run;
  }

  async function analyzeCurrentSession() {
    rememberSession();
    const session = sessionPath();
    const output = inferencePath();
    if (validationPassedFor !== session) throw new Error('session validation must pass before analysis');
    analysisPassedFor = null;
    updateWorkflowControls();
    const run = await runJobAndWait('analyze_capture', { session, output, include_motion: true });
    if (run.status === 'succeeded') analysisPassedFor = output;
    updateWorkflowControls();
    return run;
  }

  async function ingestCurrentSession() {
    rememberSession();
    const p = sessionParams();
    if (validationPassedFor !== p.session) throw new Error('session validation must pass before ingestion');
    if (analysisPassedFor !== p.inference) throw new Error('frozen analysis must succeed before ingestion');
    return runJobAndWait('ingest_capture', {
      session: p.session,
      inference: p.inference,
      source: 'motion',
      output_dir: p.output_dir,
      trial_store: p.trial_store,
    });
  }

  function bindRuntimeUi() {
    setRuntimeControls(false);
    document.querySelectorAll('[data-job]').forEach((button) => {
      button.addEventListener('click', () => runJob(button.dataset.job, {}));
    });
    $('stageSessionBtn').addEventListener('click', stageSelectedSession);
    $('validateSessionBtn').addEventListener('click', () => validateCurrentSession().catch((error) => {
      $('stageStatus').textContent = `VALIDATION REFUSED · ${error.message}`;
    }));
    $('analyzeSessionBtn').addEventListener('click', () => analyzeCurrentSession().catch((error) => {
      $('runSummary').textContent = `Analysis refused: ${error.message}`;
      $('runSummary').className = 'inline-status run-failed';
    }));
    $('ingestSessionBtn').addEventListener('click', () => ingestCurrentSession().catch((error) => {
      $('runSummary').textContent = `Ingestion refused: ${error.message}`;
      $('runSummary').className = 'inline-status run-failed';
    }));
    $('refreshWorkspaceBtn').addEventListener('click', loadWorkspace);
    ['sessionPath', 'inferencePath', 'p1OutputDir', 'trialStorePath'].forEach((id) => {
      $(id).addEventListener('change', () => {
        rememberSession();
        if (id === 'sessionPath' || id === 'inferencePath') resetWorkflowGate();
        else updateWorkflowControls();
      });
    });
  }

  bindRuntimeUi();
  loadStatus();
  checkRuntime();
  setInterval(checkRuntime, 15000);
})();
