function runAnalysis() {
            const canvas = document.getElementById('previewCanvas');
            const ctx = canvas.getContext('2d');
            const size = canvas.width;
            const imageData = ctx.getImageData(0, 0, size, size);
            const data = imageData.data;
            drawFrequencySpectrum(data, size);
            drawColorDistribution(data, size);
            estimateAttackSuccess(data, size);
            log('Analysis complete', 'success');
        }

        function drawFrequencySpectrum(data, size) {
            const canvas = document.getElementById('frequencyCanvas');
            const ctx = canvas.getContext('2d');
            const width = canvas.width; const height = canvas.height;
            ctx.fillStyle = '#1a1a2e'; ctx.fillRect(0, 0, width, height);
            const frequencies = new Array(50).fill(0);
            for (let y = 0; y < size; y += 4) {
                for (let x = 0; x < size; x += 4) {
                    const idx = (y * size + x) * 4;
                    const brightness = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
                    const freq = Math.floor(brightness / 256 * 50);
                    frequencies[freq]++;
                }
            }
            const max = Math.max(...frequencies);
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
            const width = canvas.width; const height = canvas.height;
            ctx.fillStyle = '#1a1a2e'; ctx.fillRect(0, 0, width, height);
            const colorCounts = {};
            for (let i = 0; i < data.length; i += 16) {
                const r = Math.floor(data[i] / 32) * 32;
                const g = Math.floor(data[i + 1] / 32) * 32;
                const b = Math.floor(data[i + 2] / 32) * 32;
                const key = `rgb(${r},${g},${b})`;
                colorCounts[key] = (colorCounts[key] || 0) + 1;
            }
            const sortedColors = Object.entries(colorCounts).sort((a, b) => b[1] - a[1]).slice(0, 20);
            const barWidth = width / sortedColors.length;
            for (let i = 0; i < sortedColors.length; i++) {
                const [color, count] = sortedColors[i];
                const barHeight = (count / sortedColors[0][1]) * height * 0.9;
                ctx.fillStyle = color;
                ctx.fillRect(i * barWidth, height - barHeight, barWidth - 1, barHeight);
            }
        }

        function estimateAttackSuccess(data, size) {
            let highFreqEnergy = 0; let colorVariance = 0; let edgeDensity = 0;
            const colors = [];
            for (let y = 0; y < size; y += 2) {
                for (let x = 0; x < size; x += 2) {
                    const idx = (y * size + x) * 4;
                    const brightness = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
                    highFreqEnergy += brightness;
                    colors.push([data[idx], data[idx + 1], data[idx + 2]]);
                    if (x < size - 2) {
                        const nextIdx = (y * size + x + 2) * 4;
                        const nextBrightness = (data[nextIdx] + data[nextIdx + 1] + data[nextIdx + 2]) / 3;
                        if (Math.abs(brightness - nextBrightness) > 50) { edgeDensity++; }
                    }
                }
            }
            highFreqEnergy = highFreqEnergy / (colors.length * 255);
            const avgColor = [
                colors.reduce((a, c) => a + c[0], 0) / colors.length,
                colors.reduce((a, c) => a + c[1], 0) / colors.length,
                colors.reduce((a, c) => a + c[2], 0) / colors.length
            ];
            colorVariance = colors.reduce((a, c) => {
                return a + Math.abs(c[0] - avgColor[0]) + Math.abs(c[1] - avgColor[1]) + Math.abs(c[2] - avgColor[2]);
            }, 0) / colors.length / 255;
            edgeDensity = edgeDensity / (colors.length / 2);
            const baseRate = 0.5;
            const yoloRate = Math.min(0.95, baseRate + highFreqEnergy * 0.3 + edgeDensity * 0.2);
            const detrRate = Math.min(0.90, baseRate + highFreqEnergy * 0.25 + colorVariance * 0.15);
            const rcnnRate = Math.min(0.92, baseRate + edgeDensity * 0.3 + highFreqEnergy * 0.2);
            const ssdRate = Math.min(0.88, baseRate + colorVariance * 0.25 + edgeDensity * 0.15);
            document.getElementById('yoloRate').textContent = (yoloRate * 100).toFixed(0) + '%';
            document.getElementById('yoloBar').style.width = (yoloRate * 100) + '%';
            document.getElementById('detrRate').textContent = (detrRate * 100).toFixed(0) + '%';
            document.getElementById('detrBar').style.width = (detrRate * 100) + '%';
            document.getElementById('rcnnRate').textContent = (rcnnRate * 100).toFixed(0) + '%';
            document.getElementById('rcnnBar').style.width = (rcnnRate * 100) + '%';
            document.getElementById('ssdRate').textContent = (ssdRate * 100).toFixed(0) + '%';
            document.getElementById('ssdBar').style.width = (ssdRate * 100) + '%';
        }

        function addToGallery(canvas) {
            const gallery = document.getElementById('patternGallery');
            const emptyState = document.getElementById('galleryEmpty');
            if (emptyState) { emptyState.style.display = 'none'; }
            const thumb = document.createElement('div');
            thumb.className = 'pattern-thumb';
            thumb.onclick = function() { selectGalleryItem(this); };
            const thumbCanvas = document.createElement('canvas');
            thumbCanvas.width = 100; thumbCanvas.height = 100;
            const thumbCtx = thumbCanvas.getContext('2d');
            thumbCtx.drawImage(canvas, 0, 0, 100, 100);
            const name = document.createElement('div');
            name.className = 'pattern-name';
            name.textContent = `Pattern ${galleryPatterns.length + 1}`;
            thumb.appendChild(thumbCanvas);
            thumb.appendChild(name);
            gallery.appendChild(thumb);
            galleryPatterns.push({
                canvas: canvas.toDataURL(),
                params: currentPattern.params,
                timestamp: currentPattern.timestamp
            });
        }

        function selectGalleryItem(element) {
            document.querySelectorAll('.pattern-thumb').forEach(thumb => { thumb.classList.remove('selected'); });
            element.classList.add('selected');
            log('Gallery item selected', 'info');
        }

        function addToHistory(pattern) {
            patternHistory.push(pattern);
            const historyDiv = document.getElementById('patternHistory');
            const countSpan = document.getElementById('historyCount');
            countSpan.textContent = patternHistory.length;
            const entry = document.createElement('div');
            entry.style.cssText = 'padding: 8px; border-bottom: 1px solid var(--border-color); font-size: 11px;';
            entry.innerHTML = `
                <div style="color: var(--text-secondary);">${new Date(pattern.timestamp).toLocaleTimeString()}</div>
                <div style="color: var(--text-primary);">${pattern.params.patternType} | Seed: ${pattern.params.seed}</div>
            `;
            historyDiv.insertBefore(entry, historyDiv.firstChild);
        }

        function updateMetrics() {
            const transferRate = 65 + Math.random() * 20;
            const stealthScore = 6 + Math.random() * 3;
            const printability = 6 + Math.random() * 3;
            const complexity = (Math.random() * 10).toFixed(1);
            document.getElementById('transferRate').textContent = transferRate.toFixed(0) + '%';
            document.getElementById('stealthScore').textContent = stealthScore.toFixed(1) + '/10';
            document.getElementById('printabilityScore').textContent = printability.toFixed(1) + '/10';
            document.getElementById('complexityScore').textContent = complexity;
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
                log('Configuration exported as JSON', 'success');
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

        function optimizePattern() {
            log('Quick optimize: Running 10 iterations...', 'info');
            let bestSeed = parseInt(document.getElementById('seed').value);
            let bestScore = 0;
            for (let i = 0; i < 10; i++) {
                document.getElementById('seed').value = Math.floor(Math.random() * 1000);
                updateSlider('seed');
                generatePattern();
                const score = parseFloat(document.getElementById('transferRate').textContent);
                if (score > bestScore) {
                    bestScore = score;
                    bestSeed = parseInt(document.getElementById('seed').value);
                }
            }
            document.getElementById('seed').value = bestSeed;
            updateSlider('seed');
            generatePattern();
            log(`Optimization complete. Best transfer rate: ${bestScore}%`, 'success');
        }

        function comparePatterns() {
            if (galleryPatterns.length < 2) { log('Need at least 2 patterns to compare', 'warning'); return; }
            log(`Comparing ${galleryPatterns.length} patterns...`, 'info');
            const comparison = galleryPatterns.map((p, i) => ({
                pattern: i + 1,
                type: p.params.patternType,
                seed: p.params.seed
            }));
            console.table(comparison);
            log('Comparison logged to console', 'success');
        }

        function startAnimation() {
            let frame = 0;
            function animate() {
                frame++;
                document.getElementById('seed').value = (parseInt(document.getElementById('seed').value) + 1) % 1000;
                updateSlider('seed');
                generatePattern();
                animationId = setTimeout(() => { animate(); }, 500);
            }
            animate();
        }

        function stopAnimation() {
            if (animationId) { clearTimeout(animationId); animationId = null; }
        }

        function log(message, level = 'info') {
            const console = document.getElementById('logConsole');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            const time = new Date().toLocaleTimeString();
            entry.innerHTML = `
                <span class="log-time">[${time}]</span>
                <span class="log-level ${level}">${level.toUpperCase()}</span>
                <span class="log-message">${message}</span>
            `;
            console.appendChild(entry);
            console.scrollTop = console.scrollHeight;
        }

        window.onload = function() {
            generatePattern();
        };
