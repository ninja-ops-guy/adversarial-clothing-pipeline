const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const FAMILIES = [
  'noise', 'geometric', 'organic', 'checkered',
  'machine_static', 'ghost_hound', 'broken_human', 'error_garden'
];
const SEEDS = [113, 271];

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
    await page.addScriptTag({ path: path.resolve('studio-patterns.js') });
    for (const family of FAMILIES) {
      if (!(await page.evaluate(name => typeof patternGenerators[name] === 'function', family))) {
        throw new Error(`Pattern family unavailable: ${family}`);
      }
    }
    let idx = 0;
    for (const patternType of FAMILIES) {
      for (const seed of SEEDS) {
        idx++;
        const candidateId = `RAC-POOL-V2-${String(idx).padStart(3, '0')}`;
        const scale = seed === SEEDS[0] ? 42 : 62;
        await page.selectOption('#patternType', patternType).catch(async () => {
          await page.locator('#patternType').evaluate((select, value) => {
            if (![...select.options].some(o => o.value === value)) {
              const option = document.createElement('option');
              option.value = value; option.textContent = value;
              select.appendChild(option);
            }
            select.value = value;
          }, patternType);
        });
        await page.locator('#patternScale').fill(String(scale));
        await page.locator('#colorVariance').fill('76');
        await page.locator('#edgeIntensity').fill('72');
        await page.locator('#symmetry').fill('0');
        await page.selectOption('#colorPalette', patternType === 'error_garden' ? 'earth' : 'vibrant');
        await page.locator('#seed').fill(String(seed));
        await page.evaluate(() => generatePattern());
        await page.waitForTimeout(60);
        const dataUrl = await page.locator('#previewCanvas').evaluate(c => c.toDataURL('image/png'));
        const png = Buffer.from(dataUrl.split(',')[1], 'base64');
        const pngName = `${candidateId}.png`;
        fs.writeFileSync(path.join(outputDir, pngName), png);
        records.push({
          candidate_id: candidateId,
          patternType, seed, patternScale: scale,
          colorVariance: 76, edgeIntensity: 72, symmetry: 0,
          colorPalette: patternType === 'error_garden' ? 'earth' : 'vibrant',
          png: pngName
        });
      }
    }
    fs.writeFileSync(path.join(outputDir, 'pool.json'), JSON.stringify({
      schema_version: '2.0',
      generation_policy: '16 fixed core/reference-inspired candidates; two-stage surrogate-only selection; no held-out feedback',
      candidates: records
    }, null, 2));
    console.log(`Exported ${records.length} v2 candidates to ${outputDir}`);
  } finally {
    await browser.close();
  }
}
main().catch(err => { console.error(err); process.exit(1); });
