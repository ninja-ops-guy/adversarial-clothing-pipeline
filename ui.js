function updateSlider(id) {
            const slider = document.getElementById(id);
            const valueDisplay = document.getElementById(id + 'Value');
            if (valueDisplay) { valueDisplay.textContent = slider.value; }
            if (document.getElementById('autoOptimizeToggle').classList.contains('active')) { generatePattern(); }
        }

        function updatePatternType() {
            log('Pattern type changed to: ' + document.getElementById('patternType').value, 'info');
            generatePattern();
        }

        function updateColorPalette() {
            log('Color palette changed to: ' + document.getElementById('colorPalette').value, 'info');
            generatePattern();
        }

        function toggleSwitch(id) {
            const toggle = document.getElementById(id);
            toggle.classList.toggle('active');
            const isActive = toggle.classList.contains('active');
            log(`Toggle ${id}: ${isActive ? 'ON' : 'OFF'}`, 'info');
            if (id === 'animationToggle') {
                if (isActive) { startAnimation(); } else { stopAnimation(); }
            }
        }

        function switchTab(tabName, tabEl) {
            document.querySelectorAll('.tab-content').forEach(tab => { tab.classList.remove('active'); });
            document.querySelectorAll('.tab').forEach(tab => { tab.classList.remove('active'); });
            document.getElementById(tabName).classList.add('active');
            if (tabEl) { tabEl.classList.add('active'); }
            log(`Switched to ${tabName} tab`, 'info');
            if (tabName === 'simulation') { runSimulation(); }
            if (tabName === 'analysis') { runAnalysis(); }
        }

        function generatePattern() {
            const loading = document.getElementById('previewLoading');
            loading.style.display = 'flex';
            setTimeout(() => {
                const canvas = document.getElementById('previewCanvas');
                const ctx = canvas.getContext('2d');
                const size = canvas.width;
                const params = {
                    patternType: document.getElementById('patternType').value,
                    patternScale: parseInt(document.getElementById('patternScale').value),
                    colorVariance: parseInt(document.getElementById('colorVariance').value),
                    edgeIntensity: parseInt(document.getElementById('edgeIntensity').value),
                    symmetry: parseInt(document.getElementById('symmetry').value),
                    seed: parseInt(document.getElementById('seed').value)
                };
                const palette = colorPalettes[document.getElementById('colorPalette').value];
                const rand = seededRandom(params.seed);
                ctx.fillStyle = '#1a1a2e'; ctx.fillRect(0, 0, size, size);
                const generator = patternGenerators[params.patternType];
                if (generator) { generator(ctx, size, params, palette, rand); }
                if (params.symmetry > 0) { applySymmetry(ctx, size, params.symmetry); }
                if (document.getElementById('contrastToggle').classList.contains('active')) { applyHighContrast(ctx, size); }
                currentPattern = { params: params, palette: document.getElementById('colorPalette').value, timestamp: new Date().toISOString() };
                addToHistory(currentPattern);
                updateMetrics();
                addToGallery(canvas);
                loading.style.display = 'none';
                log('Pattern generated successfully', 'success');
            }, 100);
        }

        function applySymmetry(ctx, size, symmetryType) {
            const imageData = ctx.getImageData(0, 0, size, size);
            const data = imageData.data;
            if (symmetryType === 1) {
                for (let y = 0; y < size / 2; y++) {
                    for (let x = 0; x < size; x++) {
                        const srcIdx = (y * size + x) * 4; const dstIdx = ((size - 1 - y) * size + x) * 4;
                        data[dstIdx] = data[srcIdx]; data[dstIdx + 1] = data[srcIdx + 1]; data[dstIdx + 2] = data[srcIdx + 2]; data[dstIdx + 3] = data[srcIdx + 3];
                    }
                }
            } else if (symmetryType === 2) {
                for (let y = 0; y < size; y++) {
                    for (let x = 0; x < size / 2; x++) {
                        const srcIdx = (y * size + x) * 4; const dstIdx = (y * size + (size - 1 - x)) * 4;
                        data[dstIdx] = data[srcIdx]; data[dstIdx + 1] = data[srcIdx + 1]; data[dstIdx + 2] = data[srcIdx + 2]; data[dstIdx + 3] = data[srcIdx + 3];
                    }
                }
            } else if (symmetryType === 3) {
                for (let y = 0; y < size / 2; y++) {
                    for (let x = 0; x < size / 2; x++) {
                        const srcIdx = (y * size + x) * 4;
                        const dstIdx1 = (y * size + (size - 1 - x)) * 4;
                        const dstIdx2 = ((size - 1 - y) * size + x) * 4;
                        const dstIdx3 = ((size - 1 - y) * size + (size - 1 - x)) * 4;
                        data[dstIdx1] = data[srcIdx]; data[dstIdx1 + 1] = data[srcIdx + 1]; data[dstIdx1 + 2] = data[srcIdx + 2];
                        data[dstIdx2] = data[srcIdx]; data[dstIdx2 + 1] = data[srcIdx + 1]; data[dstIdx2 + 2] = data[srcIdx + 2];
                        data[dstIdx3] = data[srcIdx]; data[dstIdx3 + 1] = data[srcIdx + 1]; data[dstIdx3 + 2] = data[srcIdx + 2];
                    }
                }
            }
            ctx.putImageData(imageData, 0, 0);
        }

        function applyHighContrast(ctx, size) {
            const imageData = ctx.getImageData(0, 0, size, size);
            const data = imageData.data;
            for (let i = 0; i < data.length; i += 4) {
                const avg = (data[i] + data[i + 1] + data[i + 2]) / 3;
                const contrast = avg > 128 ? 255 : 0;
                data[i] = contrast; data[i + 1] = contrast; data[i + 2] = contrast;
            }
            ctx.putImageData(imageData, 0, 0);
        }

        function runSimulation() {
            const canvas = document.getElementById('simulationCanvas');
            const ctx = canvas.getContext('2d');
            const size = canvas.width;
            const pose = document.getElementById('poseSelect').value;
            const fabric = document.getElementById('fabricType').value;
            const warpIntensity = parseInt(document.getElementById('warpIntensity').value);
            const lighting = document.getElementById('lightingSelect').value;
            const previewCanvas = document.getElementById('previewCanvas');
            ctx.drawImage(previewCanvas, 0, 0);
            applyFabricWarp(ctx, size, warpIntensity, fabric);
            applyPoseDeformation(ctx, size, pose);
            applyLightingEffects(ctx, size, lighting);
            log(`Simulation run: ${pose}, ${fabric}, ${lighting}`, 'success');
        }

        function applyFabricWarp(ctx, size, intensity, fabricType) {
            const imageData = ctx.getImageData(0, 0, size, size);
            const data = imageData.data;
            const newData = new Uint8ClampedArray(data);
            const fabricParams = {
                cotton: { amplitude: 1.0, frequency: 0.02 },
                polyester: { amplitude: 0.6, frequency: 0.03 },
                silk: { amplitude: 1.4, frequency: 0.015 },
                denim: { amplitude: 0.4, frequency: 0.04 }
            };
            const params = fabricParams[fabricType] || fabricParams.cotton;
            const amp = intensity / 100 * params.amplitude * 20;
            const freq = params.frequency;
            for (let y = 0; y < size; y++) {
                for (let x = 0; x < size; x++) {
                    const offsetX = Math.sin(y * freq) * amp;
                    const offsetY = Math.cos(x * freq) * amp;
                    const srcX = Math.floor(x + offsetX); const srcY = Math.floor(y + offsetY);
                    if (srcX >= 0 && srcX < size && srcY >= 0 && srcY < size) {
                        const srcIdx = (srcY * size + srcX) * 4; const dstIdx = (y * size + x) * 4;
                        newData[dstIdx] = data[srcIdx]; newData[dstIdx + 1] = data[srcIdx + 1];
                        newData[dstIdx + 2] = data[srcIdx + 2]; newData[dstIdx + 3] = data[srcIdx + 3];
                    }
                }
            }
            const newImageData = new ImageData(newData, size, size);
            ctx.putImageData(newImageData, 0, 0);
        }

        function applyPoseDeformation(ctx, size, pose) {
            const imageData = ctx.getImageData(0, 0, size, size);
            const data = imageData.data;
            if (pose === 'sitting') {
                const centerY = size / 2; const compressRange = size * 0.3;
                for (let y = 0; y < size; y++) {
                    const dist = Math.abs(y - centerY);
                    if (dist < compressRange) {
                        const compress = 1 - (1 - dist / compressRange) * 0.2;
                        const newY = centerY + (y - centerY) * compress;
                        if (Math.floor(newY) !== y) {
                            for (let x = 0; x < size; x++) {
                                const srcIdx = (y * size + x) * 4; const dstIdx = (Math.floor(newY) * size + x) * 4;
                                data[dstIdx] = data[srcIdx]; data[dstIdx + 1] = data[srcIdx + 1]; data[dstIdx + 2] = data[srcIdx + 2];
                            }
                        }
                    }
                }
            } else if (pose === 'arms_raised') {
                for (let y = 0; y < size * 0.3; y++) {
                    const stretch = 1 + (1 - y / (size * 0.3)) * 0.3;
                    for (let x = 0; x < size; x++) {
                        const newX = Math.floor(x * stretch);
                        if (newX < size) {
                            const srcIdx = (y * size + x) * 4; const dstIdx = (y * size + newX) * 4;
                            data[dstIdx] = data[srcIdx]; data[dstIdx + 1] = data[srcIdx + 1]; data[dstIdx + 2] = data[srcIdx + 2];
                        }
                    }
                }
            } else if (pose === 'walking') {
                const shearAmount = 0.1;
                for (let y = 0; y < size; y++) {
                    const offset = Math.floor(y * shearAmount);
                    for (let x = size - 1; x >= offset; x--) {
                        const srcIdx = (y * size + x - offset) * 4; const dstIdx = (y * size + x) * 4;
                        data[dstIdx] = data[srcIdx]; data[dstIdx + 1] = data[srcIdx + 1]; data[dstIdx + 2] = data[srcIdx + 2];
                    }
                }
            }
            ctx.putImageData(imageData, 0, 0);
        }

        function applyLightingEffects(ctx, size, lighting) {
            const imageData = ctx.getImageData(0, 0, size, size);
            const data = imageData.data;
            const lightingParams = {
                indoor: { brightness: 1.0, warmth: 0 },
                outdoor: { brightness: 1.1, warmth: 0.1 },
                low_light: { brightness: 0.6, warmth: 0.2 },
                direct_sun: { brightness: 1.3, warmth: 0.3 }
            };
            const params = lightingParams[lighting] || lightingParams.indoor;
            for (let i = 0; i < data.length; i += 4) {
                data[i] = Math.min(255, data[i] * params.brightness);
                data[i + 1] = Math.min(255, data[i + 1] * params.brightness);
                data[i + 2] = Math.min(255, data[i + 2] * params.brightness);
                data[i] = Math.min(255, data[i] + params.warmth * 30);
                data[i + 2] = Math.max(0, data[i + 2] - params.warmth * 20);
            }
            ctx.putImageData(imageData, 0, 0);
        }
