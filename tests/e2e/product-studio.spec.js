const { test, expect } = require('@playwright/test');
const fs = require('fs');

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('product-studio.html');
  await expect(page.locator('#mockupCanvas')).toBeVisible();
  await expect(page.locator('#studioStatus')).toContainText('READY');
  page.__errors = errors;
});

test.afterEach(async ({ page }) => {
  expect(page.__errors || []).toEqual([]);
});

test('reference design families render distinct production tiles', async ({ page }) => {
  const families = ['machine_static', 'ghost_hound', 'broken_human', 'error_garden'];
  const tails = new Set();
  for (const family of families) {
    await page.selectOption('#designFamily', family);
    await page.getByRole('button', { name: 'Render Design' }).click();
    const data = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL());
    expect(data.length).toBeGreaterThan(5000);
    tails.add(data.slice(-700));
  }
  expect(tails.size).toBe(4);
});

test('all garment mockups render', async ({ page }) => {
  for (const product of ['hoodie', 'beanie', 'cargo', 'mask', 'shirt']) {
    await page.selectOption('#productType', product);
    await page.getByRole('button', { name: 'Render Design' }).click();
    const data = await page.locator('#mockupCanvas').evaluate(c => c.toDataURL());
    expect(data.length).toBeGreaterThan(10000);
  }
});

test('studio controls update deterministic variation', async ({ page }) => {
  const before = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL().slice(-900));
  await page.locator('#studioSeed').fill('707');
  await expect(page.locator('#studioSeedValue')).toHaveText('707');
  await page.getByRole('button', { name: 'Render Design' }).click();
  const after = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL().slice(-900));
  expect(after).not.toBe(before);
  await expect(page.locator('#studioStatus')).toContainText('SEED 707');
});

test('reference board and manifest exports download non-empty files', async ({ page }) => {
  for (const name of ['Export Reference Board PNG', 'Export Production Manifest']) {
    const wait = page.waitForEvent('download');
    await page.getByRole('button', { name }).click();
    const download = await wait;
    const path = await download.path();
    expect(fs.statSync(path).size).toBeGreaterThan(200);
  }
});

test('product studio remains usable on mobile', async ({ page }) => {
  await expect(page.locator('.studio-grid')).toBeVisible();
  await page.selectOption('#productType', 'mask');
  await page.getByRole('button', { name: 'Render Design' }).click();
  await expect(page.locator('#mockupCanvas')).toBeVisible();
});
