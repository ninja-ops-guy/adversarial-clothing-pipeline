let latestMeasuredBenchmark = null;

function runAnalysis() {
    const canvas = document.getElementById('previewCanvas');
    const ctx = canvas.getContext('2d');
    const size = canvas.width;
    const imageData = ctx.getImageData(0, 0, size, size);
    const data = imageData.data;
    drawFrequencySpectrum(data, size);
    drawColorDistribution(data, size);
    loadMeasuredBenchmark();
    log('Analysis complete', 'success');
}

function drawFrequencySpectrum(data, size) {
    const canvas = document.getElementById('frequencyCanvas');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, width, height);
    const frequencies = new Array(50).fill(0);
    for (let y = 0; y < size; y += 4) {
        for (let x = 0; x < size; x += 4) {
            const idx = (y * size + x) * 4;
            const brightness = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
            const freq = Math.min(49, Math.floor(brightness / 256 * 50));
            frequencies[freq]++;
        }
    }
    const max = Math.max(...frequencies, 1);
    const barWidth = width / frequencies.length;
    for (let i = 0; i < frequencies.length; i++) {
        const barHeight = (frequencies[i] / max) * height * 0.8;
        const hue = (i / frequencies.length) * 240;
        ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
        ctx.fillRect(i * barWidth, height - barHeight, barWidth - 1, barHeight);
    }
}

function drawColorDistribution(data, size) {
    const canvas = document.getElementById('colorCanvas');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, width, height);
    const colorCounts = {};
    for (let i = 0; i < data.length; i += 16) {
        const r = Math.floor(data[i] / 32) * 32;
        const g = Math.floor(data[i + 1] / 32) * 32;
        const b = Math.floor(data[i + 2] / 32) * 32;
        const key = `rgb(${r},${g},${b})`;
        colorCounts[key] = (colorCounts[key] || 0) + 1;
    }
    const sortedColors = Object.entries(colorCounts).sort((a, b) => b[1] - a[1]).slice(0, 20);
    if (!sortedColors.length) return;
    const barWidth = width / sortedColors.length;
    for (let i = 0; i < sortedColors.length; i++) {
        const [color, count] = sortedColors[i];
        const barHeight = (count / sortedColors[0][1]) * height * 0.9;
        ctx.fillStyle = color;
        ctx.fillRect(i * barWidth, height - barHeight, barWidth - 1, barHeight);
    }
}

function patternMatchesBenchmark(result) {
    if (!currentPattern || !result?.candidate?.config) return false;
    const benchmark = result.candidate.config;
    const current = {
        patternType: currentPattern.params.patternType,
        patternScale: Number(currentPattern.params.patternScale),
        colorVariance: Number(currentPattern.params.colorVariance),
        edgeIntensity: Number(currentPattern.params.edgeIntensity),
        symmetry: Number(currentPattern.params.symmetry),
        colorPalette: currentPattern.palette,
        seed: Number(currentPattern.params.seed)
    };
    return Object.keys(current).every((key) => String(current[key]) === String(benchmark[key]));
}

function formatPercent(value, digits = 1) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
    return `${(Number(value) * 100).toFixed(digits)}%`;
}

function renderMeasuredModel(model, rateId, barId) {
    const rate = document.getElementById(rateId);
    const bar = document.getElementById(barId);
    if (!rate || !bar) return;
    if (!model || model.relative_detection_suppression === null || model.relative_detection_suppression === undefined) {
        rate.textContent = 'N/A';
        bar.style.width = '0%';
        return;
    }
    const suppression = Number(model.relative_detection_suppression);
    rate.textContent = formatPercent(suppression);
    rate.title = `Baseline detection ${formatPercent(model.baseline_detection_rate)} → candidate ${formatPercent(model.candidate_detection_rate)}; n=${model.n}`;
    bar.style.width = `${Math.max(0, Math.min(100, suppression * 100))}%`;
}

function renderMeasuredBenchmark(result) {
    latestMeasuredBenchmark = result;
    const models = result.models || {};
    renderMeasuredModel(models.yolov8n, 'yoloRate', 'yoloBar');
    renderMeasuredModel(models.detr_resnet50, 'detrRate', 'detrBar');
    renderMeasuredModel(models.fasterrcnn_mobilenet_v3_320, 'rcnnRate', 'rcnnBar');
    renderMeasuredModel(models.ssdlite320_mobilenet_v3, 'ssdRate', 'ssdBar');

    const matches = patternMatchesBenchmark(result);
    const transfer = document.getElementById('transferRate');
    if (transfer) {
        transfer.textContent = matches ? formatPercent(result.aggregate?.relative_detection_suppression) : '--';
        transfer.title = matches
            ? 'Measured aggregate relative detection suppression for the canonical CI fixture.'
            : 'Latest measured benchmark is for a different Pattern Lab configuration.';
    }

    const status = document.getElementById('benchmarkStatus');
    if (status) {
        const generated = result.generated_at ? new Date(result.generated_at).toLocaleString() : 'unknown time';
        const commit = String(result.source_commit || 'unknown').slice(0, 8);
        const sampleCount = result.fixture?.sample_count ?? '?';
        const conditions = result.benchmark?.conditions_per_model ?? '?';
        status.innerHTML = `
            <div><strong>MEASURED</strong> · ${matches ? 'current pattern matches benchmark candidate' : 'showing canonical candidate; current pattern differs'}</div>
            <div style="margin-top:6px;color:var(--text-secondary);">${sampleCount} digital samples × ${conditions} transform conditions/model · commit ${commit} · ${generated}</div>
        `;
    }

    const caveat = document.getElementById('benchmarkCaveat');
    if (caveat) {
        caveat.textContent = result.caveats?.[0] || 'Measured digital inference result; not a physical garment claim.';
    }
}

function resetMeasuredDisplay(message) {
    [['yoloRate', 'yoloBar'], ['detrRate', 'detrBar'], ['rcnnRate', 'rcnnBar'], ['ssdRate', 'ssdBar']].forEach(([rateId, barId]) => {
        const rate = document.getElementById(rateId);
        const bar = document.getElementById(barId);
        if (rate) rate.textContent = 'N/A';
        if (bar) bar.style.width = '0%';
    });
    const transfer = document.getElementById('transferRate');
    if (transfer) transfer.textContent = '--';
    const status = document.getElementById('benchmarkStatus');
    if (status) status.textContent = message;
}

async function loadMeasuredBenchmark() {
    try {
        const response = await fetch(`benchmark-results.json?cache=${Date.now()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (result.status !== 'measured' || !result.models) throw new Error('benchmark payload is not a measured result');
        renderMeasuredBenchmark(result);
        log('Loaded measured detector benchmark', 'success');
        return result;
    } catch (error) {
        resetMeasuredDisplay('Measured detector benchmark is not available yet. The CI benchmark workflow must complete successfully.');
        log(`Measured benchmark unavailable: ${error.message}`, 'warning');
        return null;
    }
}

function computeLocalPatternMetrics() {
    const canvas = document.getElementById('previewCanvas');
    const ctx = canvas.getContext('2d');
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = image.data;
    const width = image.width;
    const height = image.height;
    const bins = new Array(32).fill(0);
    const colors = new Set();
    let samples = 0;
    let edges = 0;
    let comparisons = 0;

    for (let y = 0; y < height; y += 4) {
        for (let x = 0; x < width; x += 4) {
            const idx = (y * width + x) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const b = data[idx + 2];
            const gray = (r + g + b) / 3;
            bins[Math.min(31, Math.floor(gray / 8))]++;
            colors.add(`${Math.floor(r / 32)}-${Math.floor(g / 32)}-${Math.floor(b / 32)}`);
            samples++;
            if (x + 4 < width) {
                const next = (y * width + x + 4) * 4;
                const nextGray = (data[next] + data[next + 1] + data[next + 2]) / 3;
                if (Math.abs(gray - nextGray) > 48) edges++;
                comparisons++;
            }
        }
    }

    let entropy = 0;
    bins.forEach((count) => {
        if (!count) return;
        const p = count / Math.max(samples, 1);
        entropy -= p * Math.log2(p);
    });
    const entropyScore = Math.min(10, (entropy / 5) * 10);
    const edgeDensity = edges / Math.max(comparisons, 1);
    const colorComplexity = Math.min(1, colors.size / 128);
    const complexity = Math.min(10, (edgeDensity * 0.65 + colorComplexity * 0.35) * 10);
    const printability = Math.max(0, Math.min(10, 10 - edgeDensity * 4 - colorComplexity * 2));
    const localObjective = Math.max(0, Math.min(10, entropyScore * 0.45 + complexity * 0.35 + printability * 0.20));
    return { entropyScore, printability, complexity, localObjective };
}

function addToGallery(canvas) {
    const gallery = document.getElementById('patternGallery');
    const emptyState = document.getElementById('galleryEmpty');
    if (emptyState) emptyState.style.display = 'none';
    const thumb = document.createElement('div');
    thumb.className = 'pattern-thumb';
    thumb.onclick = function() { selectGalleryItem(this); };
    const thumbCanvas = document.createElement('canvas');
    thumbCanvas.width = 100;
    thumbCanvas.height = 100;
    thumbCanvas.getContext('2d').drawImage(canvas, 0, 0, 100, 100);
    const name = document.createElement('div');
    name.className = 'pattern-name';
    name.textContent = `Pattern ${galleryPatterns.length + 1}`;
    thumb.appendChild(thumbCanvas);
    thumb.appendChild(name);
    gallery.appendChild(thumb);
    galleryPatterns.push({ canvas: canvas.toDataURL(), params: currentPattern.params, timestamp: currentPattern.timestamp });
}

function selectGalleryItem(element) {
    document.querySelectorAll('.pattern-thumb').forEach(thumb => thumb.classList.remove('selected'));
    element.classList.add('selected');
    log('Gallery item selected', 'info');
}

function addToHistory(pattern) {
    patternHistory.push(pattern);
    const historyDiv = document.getElementById('patternHistory');
    document.getElementById('historyCount').textContent = patternHistory.length;
    const entry = document.createElement('div');
    entry.style.cssText = 'padding: 8px; border-bottom: 1px solid var(--border-color); font-size: 11px;';
    entry.innerHTML = `
        <div style="color: var(--text-secondary);">${new Date(pattern.timestamp).toLocaleTimeString()}</div>
        <div style="color: var(--text-primary);">${pattern.params.patternType} | Seed: ${pattern.params.seed}</div>
    `;
    historyDiv.insertBefore(entry, historyDiv.firstChild);
}

function updateMetrics() {
    const local = computeLocalPatternMetrics();
    document.getElementById('stealthScore').textContent = local.entropyScore.toFixed(1) + '/10';
    document.getElementById('printabilityScore').textContent = local.printability.toFixed(1) + '/10';
    document.getElementById('complexityScore').textContent = local.complexity.toFixed(1);
    if (latestMeasuredBenchmark) {
        renderMeasuredBenchmark(latestMeasuredBenchmark);
    } else {
        document.getElementById('transferRate').textContent = '--';
    }
}

function exportPattern(format) {
    if (!currentPattern) { log('No pattern to export', 'warning'); return; }
    if (format === 'png') {
        const canvas = document.getElementById('previewCanvas');
        const link = document.createElement('a');
        link.download = `adversarial_pattern_${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
        log('Pattern exported as PNG', 'success');
    } else if (format === 'json') {
        const config = { ...currentPattern, version: '2.0.0', exported: new Date().toISOString() };
        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');
        link.download = `adversarial_config_${Date.now()}.json`;
        link.href = URL.createObjectURL(blob);
        link.click();
        URL.revokeObjectURL(link.href);
        log('Configuration exported as JSON', 'success');
    } else if (format === 'svg') {
        const canvas = document.getElementById('previewCanvas');
        const pngData = canvas.toDataURL('image/png');
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}" viewBox="0 0 ${canvas.width} ${canvas.height}"><image width="100%" height="100%" href="${pngData}"/></svg>`;
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const link = document.createElement('a');
        link.download = `adversarial_pattern_${Date.now()}.svg`;
        link.href = URL.createObjectURL(blob);
        link.click();
        URL.revokeObjectURL(link.href);
        log('Pattern exported as SVG', 'success');
    }
}

function exportConfig() {
    const config = {
        version: '2.0.0',
        timestamp: new Date().toISOString(),
        controls: {
            patternType: document.getElementById('patternType').value,
            patternScale: document.getElementById('patternScale').value,
            colorVariance: document.getElementById('colorVariance').value,
            edgeIntensity: document.getElementById('edgeIntensity').value,
            symmetry: document.getElementById('symmetry').value,
            colorPalette: document.getElementById('colorPalette').value,
            seed: document.getElementById('seed').value
        },
        simulation: {
            pose: document.getElementById('poseSelect').value,
            fabricType: document.getElementById('fabricType').value,
            warpIntensity: document.getElementById('warpIntensity').value,
            lighting: document.getElementById('lightingSelect').value
        }
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.download = `lab_config_${Date.now()}.json`;
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
    log('Lab configuration exported', 'success');
}

function resetAll() {
    document.getElementById('patternType').value = 'noise';
    document.getElementById('patternScale').value = 50;
    document.getElementById('colorVariance').value = 70;
    document.getElementById('edgeIntensity').value = 60;
    document.getElementById('symmetry').value = 0;
    document.getElementById('colorPalette').value = 'vibrant';
    document.getElementById('seed').value = 42;
    document.querySelectorAll('.toggle').forEach(t => t.classList.remove('active'));
    patternHistory = [];
    galleryPatterns = [];
    document.getElementById('patternHistory').innerHTML = '';
    document.getElementById('historyCount').textContent = '0';
    document.getElementById('patternGallery').innerHTML = '';
    document.getElementById('galleryEmpty').style.display = 'block';
    log('All settings reset', 'info');
}

function randomizePattern() {
    document.getElementById('patternType').value = Object.keys(patternGenerators)[Math.floor(Math.random() * 8)];
    document.getElementById('patternScale').value = Math.floor(Math.random() * 96) + 5;
    document.getElementById('colorVariance').value = Math.floor(Math.random() * 101);
    document.getElementById('edgeIntensity').value = Math.floor(Math.random() * 101);
    document.getElementById('symmetry').value = Math.floor(Math.random() * 5);
    document.getElementById('colorPalette').value = Object.keys(colorPalettes)[Math.floor(Math.random() * 8)];
    document.getElementById('seed').value = Math.floor(Math.random() * 1000);
    ['patternScale', 'colorVariance', 'edgeIntensity', 'symmetry', 'seed'].forEach(id => updateSlider(id));
    generatePattern();
    log('Parameters randomized', 'success');
}

async function optimizePattern() {
    log('Quick optimize: Running 10 seeds against the local visual/printability proxy...', 'info');
    let bestSeed = parseInt(document.getElementById('seed').value);
    let bestScore = -Infinity;
    for (let i = 0; i < 10; i++) {
        document.getElementById('seed').value = Math.floor(Math.random() * 1000);
        updateSlider('seed');
        await generatePattern();
        const score = computeLocalPatternMetrics().localObjective;
        if (score > bestScore) {
            bestScore = score;
            bestSeed = parseInt(document.getElementById('seed').value);
        }
    }
    document.getElementById('seed').value = bestSeed;
    updateSlider('seed');
    await generatePattern();
    log(`Optimization complete. Best local proxy score: ${bestScore.toFixed(2)}/10. Detector efficacy requires the measured benchmark workflow.`, 'success');
}

function comparePatterns() {
    if (galleryPatterns.length < 2) { log('Need at least 2 patterns to compare', 'warning'); return; }
    log(`Comparing ${galleryPatterns.length} patterns...`, 'info');
    const comparison = galleryPatterns.map((p, i) => ({ pattern: i + 1, type: p.params.patternType, seed: p.params.seed }));
    console.table(comparison);
    log('Comparison logged to console', 'success');
}

function startAnimation() {
    function animate() {
        document.getElementById('seed').value = (parseInt(document.getElementById('seed').value) + 1) % 1000;
        updateSlider('seed');
        generatePattern();
        animationId = setTimeout(animate, 500);
    }
    animate();
}

function stopAnimation() {
    if (animationId) {
        clearTimeout(animationId);
        animationId = null;
    }
}

function log(message, level = 'info') {
    const consoleEl = document.getElementById('logConsole');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const time = new Date().toLocaleTimeString();
    entry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-level ${level}">${level.toUpperCase()}</span>
        <span class="log-message">${message}</span>
    `;
    consoleEl.appendChild(entry);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

window.onload = async function() {
    await generatePattern();
    await loadMeasuredBenchmark();
};
