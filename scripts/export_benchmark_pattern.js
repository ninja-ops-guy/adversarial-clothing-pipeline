const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

async function main() {
  const outputDir = path.resolve(process.argv[2] || 'benchmarks/runtime');
  fs.mkdirSync(outputDir, { recursive: true });

  const baseURL = process.env.PATTERN_LAB_URL || 'http://127.0.0.1:4173';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  try {
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.currentPattern !== null || document.querySelector('#historyCount')?.textContent !== '0');

    const config = {
      patternType: process.env.BENCHMARK_PATTERN_TYPE || 'noise',
      patternScale: Number(process.env.BENCHMARK_PATTERN_SCALE || 50),
      colorVariance: Number(process.env.BENCHMARK_COLOR_VARIANCE || 70),
      edgeIntensity: Number(process.env.BENCHMARK_EDGE_INTENSITY || 60),
      symmetry: Number(process.env.BENCHMARK_SYMMETRY || 0),
      colorPalette: process.env.BENCHMARK_COLOR_PALETTE || 'vibrant',
      seed: Number(process.env.BENCHMARK_SEED || 42)
    };

    await page.selectOption('#patternType', config.patternType);
    await page.locator('#patternScale').fill(String(config.patternScale));
    await page.locator('#colorVariance').fill(String(config.colorVariance));
    await page.locator('#edgeIntensity').fill(String(config.edgeIntensity));
    await page.locator('#symmetry').fill(String(config.symmetry));
    await page.selectOption('#colorPalette', config.colorPalette);
    await page.locator('#seed').fill(String(config.seed));
    await page.evaluate(() => generatePattern());
    await page.waitForTimeout(150);

    const payload = await page.locator('#previewCanvas').evaluate((canvas) => ({
      png: canvas.toDataURL('image/png'),
      width: canvas.width,
      height: canvas.height
    }));

    const png = Buffer.from(payload.png.split(',')[1], 'base64');
    fs.writeFileSync(path.join(outputDir, 'candidate.png'), png);
    fs.writeFileSync(path.join(outputDir, 'candidate-config.json'), JSON.stringify({
      schema_version: '1.0',
      source: 'Pattern Lab browser canvas',
      width: payload.width,
      height: payload.height,
      ...config
    }, null, 2));

    console.log(`Exported ${png.length} byte candidate pattern to ${outputDir}`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
