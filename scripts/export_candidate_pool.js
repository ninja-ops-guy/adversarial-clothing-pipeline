const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const POOL = [
  ['noise', 101],
  ['geometric', 131],
  ['organic', 151],
  ['checkered', 181],
  ['striped', 211],
  ['circular', 241],
  ['cellular', 271],
  ['perlin', 307]
];

async function main() {
  const outputDir = path.resolve(process.argv[2] || 'benchmarks/runtime/pool');
  fs.mkdirSync(outputDir, { recursive: true });
  const baseURL = process.env.PATTERN_LAB_URL || 'http://127.0.0.1:4173';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const records = [];
  try {
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => document.querySelector('#historyCount')?.textContent !== '0');
    for (let i = 0; i < POOL.length; i++) {
      const [patternType, seed] = POOL[i];
      const candidateId = `RAC-POOL-${String(i + 1).padStart(3, '0')}`;
      await page.selectOption('#patternType', patternType);
      await page.locator('#patternScale').fill('50');
      await page.locator('#colorVariance').fill('70');
      await page.locator('#edgeIntensity').fill('60');
      await page.locator('#symmetry').fill('0');
      await page.selectOption('#colorPalette', 'vibrant');
      await page.locator('#seed').fill(String(seed));
      await page.evaluate(() => generatePattern());
      await page.waitForTimeout(80);
      const dataUrl = await page.locator('#previewCanvas').evaluate(c => c.toDataURL('image/png'));
      const png = Buffer.from(dataUrl.split(',')[1], 'base64');
      const pngName = `${candidateId}.png`;
      fs.writeFileSync(path.join(outputDir, pngName), png);
      records.push({
        candidate_id: candidateId,
        patternType,
        seed,
        patternScale: 50,
        colorVariance: 70,
        edgeIntensity: 60,
        symmetry: 0,
        colorPalette: 'vibrant',
        png: pngName
      });
    }
    fs.writeFileSync(path.join(outputDir, 'pool.json'), JSON.stringify({
      schema_version: '1.0',
      generation_policy: 'fixed preregistered eight-type pool; no held-out feedback',
      candidates: records
    }, null, 2));
    console.log(`Exported ${records.length} deterministic candidates to ${outputDir}`);
  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
