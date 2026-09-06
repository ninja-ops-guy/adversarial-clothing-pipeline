const { test, expect } = require('@playwright/test');
const fs = require('fs');

const vendorTemplate = {
  schema_version: '1.0',
  provider: 'TEST_POD',
  product_id: 'hoodie-aop-test',
  product_name: 'Test AOP Hoodie',
  template_version: '2026.09',
  source: 'Synthetic E2E fixture',
  vendor_ready: true,
  units: 'px',
  dpi: 300,
  canvas: { width: 1200, height: 900 },
  panels: [
    { id: 'front', label: 'Front', x: 20, y: 20, width: 520, height: 780, bleed: 20, safe_margin: 32, continuity_group: 'torso', required: true },
    { id: 'back', label: 'Back', x: 570, y: 20, width: 520, height: 780, bleed: 20, safe_margin: 32, continuity_group: 'torso', required: true }
  ],
  seams: [
    { a: 'front', edge_a: 'left', b: 'back', edge_b: 'right', reverse: false }
  ]
};

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('production-studio.html');
  await expect(page.locator('#panelMap')).toBeVisible();
  await expect(page.locator('#productionStatus')).toContainText('DRAFT READY');
  page.__errors = errors;
});

test.afterEach(async ({ page }) => {
  expect(page.__errors || []).toEqual([]);
});

test('generic template is explicitly draft-only and renders all normalized panels', async ({ page }) => {
  await expect(page.locator('#templateMeta')).toContainText('GENERIC_PREVIEW');
  await expect(page.locator('#templateMeta')).toContainText('draft / normalized');
  await expect(page.locator('.panel-row')).toHaveCount(6);
  const data = await page.locator('#panelMap').evaluate(c => c.toDataURL());
  expect(data.length).toBeGreaterThan(5000);
  await expect(page.locator('#validationList')).toContainText('draft-only');
});

test('imports exact vendor template and exposes panel dimensions', async ({ page }) => {
  await page.locator('#templateFile').setInputFiles({
    name: 'vendor-template.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(vendorTemplate))
  });
  await expect(page.locator('#productionStatus')).toContainText('IMPORTED TEMPLATE');
  await expect(page.locator('#templateMeta')).toContainText('TEST_POD');
  await expect(page.locator('.panel-row')).toHaveCount(2);
  await expect(page.locator('.panel-row').first()).toContainText('520×780px');
  await expect(page.locator('#validationList')).toContainText('pass local validation');
});

test('panel transforms trigger continuity warning and auto-map clears it', async ({ page }) => {
  await page.locator('#templateFile').setInputFiles({
    name: 'vendor-template.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(vendorTemplate))
  });
  await page.locator('.panel-row').nth(1).click();
  await page.locator('#offsetX').fill('77');
  await expect(page.locator('#validationList')).toContainText('inconsistent transforms');
  await page.getByRole('button', { name: 'Auto-Map Continuity Groups' }).click();
  await expect(page.locator('#validationList')).toContainText('pass local validation');
});

test('loads Product Studio state from local storage', async ({ page }) => {
  await page.evaluate(() => localStorage.setItem('rac.productStudioState', JSON.stringify({
    schema_version: '1.0', productType: 'shirt', designFamily: 'auto', studioSeed: '707', studioScale: '61', studioDensity: '55', studioDistress: '82'
  })));
  await page.getByRole('button', { name: 'Load Current Product Studio Design' }).click();
  await expect(page.locator('#family')).toHaveValue('error_garden');
  await expect(page.locator('#seed')).toHaveValue('707');
  await expect(page.locator('#productionStatus')).toContainText('SEED 707');
});

test('batch design factory ranks deterministic candidates', async ({ page }) => {
  await page.locator('#batchCount').fill('12');
  await page.locator('#batchKeep').fill('6');
  await page.getByRole('button', { name: 'Generate & Rank Seeds' }).click();
  await expect(page.locator('.candidate')).toHaveCount(6);
  await page.locator('.candidate').first().click();
  await expect(page.locator('.candidate.selected')).toHaveCount(1);
  await expect(page.locator('#exportBatchBtn')).toBeEnabled();
});

test('exports a hash-bound vendor panel pack zip', async ({ page, browserName }) => {
  test.skip(browserName === 'webkit', 'Large 4096px PNG hashing is covered in Chromium to keep mobile CI bounded.');
  await page.locator('#templateFile').setInputFiles({
    name: 'vendor-template.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(vendorTemplate))
  });
  const wait = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export Panel Pack ZIP' }).click();
  const download = await wait;
  expect(download.suggestedFilename()).toMatch(/^rac-vendor-panel-pack-.*\.zip$/);
  const path = await download.path();
  const bytes = fs.readFileSync(path);
  expect(bytes.length).toBeGreaterThan(1000);
  const text = bytes.toString('latin1');
  expect(text).toContain('master/repeat_4096.png');
  expect(text).toContain('panels/front.png');
  expect(text).toContain('manifest.json');
  await expect(page.locator('#hashMetrics')).toContainText('Design SHA-256');
});

test('production mapper remains usable on mobile', async ({ page }) => {
  await expect(page.locator('.layout')).toBeVisible();
  await page.locator('.panel-row').first().click();
  await page.locator('#panelScale').fill('130');
  await expect(page.locator('#panelScaleValue')).toHaveText('130');
  await expect(page.locator('#panelMap')).toBeVisible();
});


test('rejects malformed or unsafe vendor templates', async ({ page }) => {
  const bad = JSON.parse(JSON.stringify(vendorTemplate));
  bad.canvas.width = 100;
  bad.panels[0].width = 999999;
  await page.locator('#templateFile').setInputFiles({
    name: 'bad-template.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(bad))
  });
  await expect(page.locator('#productionStatus')).toContainText('TEMPLATE ERROR');
  await expect(page.locator('#productionStatus')).toContainText(/safety limit|canvas bounds/);
});

test('rejects duplicate panel ids and broken seam references', async ({ page }) => {
  const bad = JSON.parse(JSON.stringify(vendorTemplate));
  bad.panels[1].id = 'front';
  bad.seams[0].b = 'missing';
  await page.locator('#templateFile').setInputFiles({
    name: 'bad-seams.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(bad))
  });
  await expect(page.locator('#productionStatus')).toContainText('TEMPLATE ERROR');
  await expect(page.locator('#productionStatus')).toContainText(/duplicate panel id|missing panel/);
});
