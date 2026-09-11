let manualMeasuredOverrideActive = false;

async function importMeasuredResults(file) {
    if (!file) return;
    const evidence = document.getElementById('measuredEvidence');
    try {
        const text = await file.text();
        const result = JSON.parse(text);
        const measuredStatuses = new Set(['measured_locked', 'measured_unlocked']);
        if (!measuredStatuses.has(result.status) || !result.models) {
            throw new Error('Expected a measured_locked or measured_unlocked benchmark-results.json payload');
        }
        // Once a user explicitly accepts a manual measured artifact, keep that
        // artifact authoritative for the remainder of the page session. An
        // already-in-flight automatic benchmark fetch must not race in later
        // and silently replace the displayed provenance/result.
        manualMeasuredOverrideActive = true;
        renderMeasuredBenchmark(result);
        if (evidence) {
            const commit = String(result.source_commit || 'unknown').slice(0, 8);
            evidence.textContent = `Manual measured result loaded · commit ${commit} · ${result.fixture?.sample_count ?? '?'} samples.`;
        }
        log('Manual measured benchmark JSON loaded', 'success');
    } catch (error) {
        if (evidence) evidence.textContent = `Import failed: ${error.message}`;
        log(`Measured benchmark import failed: ${error.message}`, 'error');
    }
}

// Keep the browser's automatic benchmark loader on the same locked schema
// enforced by the measured-benchmark workflow and manual import path.
async function loadMeasuredBenchmark() {
    if (manualMeasuredOverrideActive) return latestMeasuredBenchmark;
    try {
        const response = await fetch(`benchmark-results.json?cache=${Date.now()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        const measuredStatuses = new Set(['measured_locked', 'measured_unlocked']);
        if (!measuredStatuses.has(result.status) || !result.models) {
            throw new Error('benchmark payload is not a locked/unlocked measured result');
        }
        // The fetch may have started before a manual import completed. Check
        // again after the await so automatic data can never overwrite an
        // accepted manual override.
        if (manualMeasuredOverrideActive) return latestMeasuredBenchmark;
        renderMeasuredBenchmark(result);
        log('Loaded measured detector benchmark', 'success');
        return result;
    } catch (error) {
        if (manualMeasuredOverrideActive) return latestMeasuredBenchmark;
        resetMeasuredDisplay('Measured detector benchmark is not available yet. The CI benchmark workflow must complete successfully.');
        log(`Measured benchmark unavailable: ${error.message}`, 'warning');
        return null;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const actions = document.querySelector('.header-actions');
    if (!actions || document.getElementById('productStudioLink')) return;
    const link = document.createElement('a');
    link.id = 'productStudioLink';
    link.className = 'btn btn-secondary';
    link.href = 'product-studio.html';
    link.style.textDecoration = 'none';
    link.innerHTML = '<span>🧵</span> Product Studio';
    actions.prepend(link);
});
