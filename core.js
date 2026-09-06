let currentPattern = null;
        let patternHistory = [];
        let galleryPatterns = [];
        let animationId = null;
        let selectedGalleryIndex = -1;

        function seededRandom(seed) {
            let s = seed;
            return function() {
                s = (s * 9301 + 49297) % 233280;
                return s / 233280;
            };
        }

        const colorPalettes = {
            vibrant: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'],
            monochrome: ['#000000', '#333333', '#666666', '#999999', '#CCCCCC', '#FFFFFF'],
            earth: ['#8B4513', '#D2691E', '#CD853F', '#DEB887', '#F5DEB3', '#556B2F', '#6B8E23'],
            cool: ['#1E3A8A', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#0EA5E9', '#06B6D4'],
            warm: ['#DC2626', '#EA580C', '#F97316', '#FB923C', '#FDBA74', '#FECACA', '#FEE2E2'],
            pastel: ['#FBCFE8', '#FCE7F3', '#DDD6FE', '#E0E7FF', '#C7D2FE', '#BAE6FD', '#B6F0C8'],
            neon: ['#FF00FF', '#00FFFF', '#FFFF00', '#FF0080', '#00FF80', '#8000FF', '#FF8000'],
            stealth: ['#1a1a2e', '#16213e', '#0f3460', '#533483', '#e94560', '#0a0a0a', '#2d2d44']
        };

        const patternGenerators = {
            noise: function(ctx, size, params, palette, rand) {
                const imageData = ctx.createImageData(size, size);
                const data = imageData.data;
                const colors = palette.map(hex => {
                    const r = parseInt(hex.slice(1, 3), 16);
                    const g = parseInt(hex.slice(3, 5), 16);
                    const b = parseInt(hex.slice(5, 7), 16);
                    return [r, g, b];
                });
                for (let y = 0; y < size; y++) {
                    for (let x = 0; x < size; x++) {
                        const idx = (y * size + x) * 4;
                        if (rand() < params.colorVariance / 100) {
                            const color = colors[Math.floor(rand() * colors.length)];
                            data[idx] = color[0]; data[idx + 1] = color[1]; data[idx + 2] = color[2];
                        } else {
                            const gray = Math.floor(rand() * 255);
                            data[idx] = gray; data[idx + 1] = gray; data[idx + 2] = gray;
                        }
                        data[idx + 3] = 255;
                    }
                }
                ctx.putImageData(imageData, 0, 0);
            },
            geometric: function(ctx, size, params, palette, rand) {
                const colors = palette;
                const scale = params.patternScale / 10;
                for (let i = 0; i < 50; i++) {
                    ctx.fillStyle = colors[Math.floor(rand() * colors.length)];
                    ctx.strokeStyle = colors[Math.floor(rand() * colors.length)];
                    ctx.lineWidth = 2 + rand() * params.edgeIntensity / 10;
                    const x = rand() * size; const y = rand() * size;
                    const w = (20 + rand() * 80) * scale / 5; const h = (20 + rand() * 80) * scale / 5;
                    const type = Math.floor(rand() * 4);
                    if (type === 0) { ctx.fillRect(x, y, w, h); }
                    else if (type === 1) { ctx.beginPath(); ctx.arc(x, y, w / 2, 0, Math.PI * 2); ctx.fill(); }
                    else if (type === 2) { ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w / 2, y + h); ctx.closePath(); ctx.fill(); }
                    else { ctx.strokeRect(x, y, w, h); }
                }
            },
            organic: function(ctx, size, params, palette, rand) {
                const colors = palette;
                for (let i = 0; i < 30; i++) {
                    ctx.fillStyle = colors[Math.floor(rand() * colors.length)] + '80';
                    ctx.strokeStyle = colors[Math.floor(rand() * colors.length)];
                    ctx.lineWidth = 1 + rand() * 3;
                    const cx = rand() * size; const cy = rand() * size;
                    const baseRadius = 20 + rand() * 60 * params.patternScale / 50;
                    ctx.beginPath();
                    for (let angle = 0; angle < Math.PI * 2; angle += 0.1) {
                        const radius = baseRadius * (0.7 + 0.3 * Math.sin(angle * (3 + rand() * 5)));
                        const x = cx + Math.cos(angle) * radius; const y = cy + Math.sin(angle) * radius;
                        if (angle === 0) { ctx.moveTo(x, y); } else { ctx.lineTo(x, y); }
                    }
                    ctx.closePath(); ctx.fill(); ctx.stroke();
                }
            },
            checkered: function(ctx, size, params, palette, rand) {
                const colors = palette;
                const cellSize = params.patternScale * 2 + 10;
                for (let y = 0; y < size; y += cellSize) {
                    for (let x = 0; x < size; x += cellSize) {
                        const colorIdx = Math.floor(rand() * colors.length);
                        ctx.fillStyle = colors[colorIdx];
                        ctx.fillRect(x, y, cellSize, cellSize);
                        if (params.edgeIntensity > 30) {
                            ctx.strokeStyle = colors[(colorIdx + 1) % colors.length];
                            ctx.lineWidth = params.edgeIntensity / 20;
                            ctx.strokeRect(x, y, cellSize, cellSize);
                        }
                    }
                }
            },
            striped: function(ctx, size, params, palette, rand) {
                const colors = palette;
                const stripeWidth = params.patternScale / 2 + 5;
                const stripeCount = Math.ceil(size / stripeWidth);
                for (let i = 0; i < stripeCount; i++) {
                    ctx.fillStyle = colors[i % colors.length];
                    ctx.fillRect(i * stripeWidth, 0, stripeWidth, size);
                }
                if (params.edgeIntensity > 50) {
                    ctx.strokeStyle = colors[0]; ctx.lineWidth = 2;
                    for (let i = 0; i < stripeCount; i++) {
                        ctx.beginPath(); ctx.moveTo(i * stripeWidth, 0); ctx.lineTo(i * stripeWidth, size); ctx.stroke();
                    }
                }
            },
            circular: function(ctx, size, params, palette, rand) {
                const colors = palette;
                const cx = size / 2; const cy = size / 2; const maxRadius = size / 2;
                const ringCount = 10 + params.patternScale / 5;
                for (let i = ringCount; i > 0; i--) {
                    const radius = (i / ringCount) * maxRadius;
                    ctx.fillStyle = colors[i % colors.length];
                    ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fill();
                }
            },
            cellular: function(ctx, size, params, palette, rand) {
                const colors = palette;
                const cellSize = params.patternScale / 3 + 8;
                const gridSize = Math.ceil(size / cellSize);
                let grid = [];
                for (let y = 0; y < gridSize; y++) {
                    grid[y] = [];
                    for (let x = 0; x < gridSize; x++) { grid[y][x] = rand() > 0.5 ? 1 : 0; }
                }
                const iterations = 3 + Math.floor(params.edgeIntensity / 20);
                for (let iter = 0; iter < iterations; iter++) {
                    const newGrid = [];
                    for (let y = 0; y < gridSize; y++) {
                        newGrid[y] = [];
                        for (let x = 0; x < gridSize; x++) {
                            let neighbors = 0;
                            for (let dy = -1; dy <= 1; dy++) {
                                for (let dx = -1; dx <= 1; dx++) {
                                    if (dx === 0 && dy === 0) continue;
                                    const ny = (y + dy + gridSize) % gridSize;
                                    const nx = (x + dx + gridSize) % gridSize;
                                    neighbors += grid[ny][nx];
                                }
                            }
                            newGrid[y][x] = neighbors === 3 || (grid[y][x] === 1 && neighbors === 2) ? 1 : 0;
                        }
                    }
                    grid = newGrid;
                }
                for (let y = 0; y < gridSize; y++) {
                    for (let x = 0; x < gridSize; x++) {
                        if (grid[y][x]) {
                            ctx.fillStyle = colors[Math.floor(rand() * colors.length)];
                            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
                        }
                    }
                }
            },
            perlin: function(ctx, size, params, palette, rand) {
                const colors = palette;
                const scale = params.patternScale / 20;
                const octaves = 4;
                function noise(x, y) { return rand() * 0.5 + 0.5 * Math.sin(x * 0.1) * Math.cos(y * 0.1); }
                const imageData = ctx.createImageData(size, size);
                const data = imageData.data;
                for (let y = 0; y < size; y++) {
                    for (let x = 0; x < size; x++) {
                        let value = 0; let amplitude = 1; let frequency = scale / 100;
                        for (let o = 0; o < octaves; o++) {
                            value += noise(x * frequency, y * frequency) * amplitude;
                            amplitude *= 0.5; frequency *= 2;
                        }
                        const rawIdx = Math.floor(value * colors.length);
                        const colorIdx = ((rawIdx % colors.length) + colors.length) % colors.length;
                        const color = colors[colorIdx];
                        const r = parseInt(color.slice(1, 3), 16);
                        const g = parseInt(color.slice(3, 5), 16);
                        const b = parseInt(color.slice(5, 7), 16);
                        const idx = (y * size + x) * 4;
                        data[idx] = r; data[idx + 1] = g; data[idx + 2] = b; data[idx + 3] = 255;
                    }
                }
                ctx.putImageData(imageData, 0, 0);
            }
        };
