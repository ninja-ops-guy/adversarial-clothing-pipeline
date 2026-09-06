async function importMeasuredResults(file) {
    if (!file) return;
    const evidence = document.getElementById('measuredEvidence');
    try {
        const text = await file.text();
        const result = JSON.parse(text);
        if (result.status !== 'measured' || !result.models) {
            throw new Error('Expected a measured benchmark-results.json payload');
        }
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
