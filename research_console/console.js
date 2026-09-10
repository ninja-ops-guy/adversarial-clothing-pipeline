(() => {
  'use strict';

  const target = document.getElementById('experimentStatus');
  if (!target) return;

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

  loadStatus();
})();
