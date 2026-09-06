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
  const families = ['signal_shadow', 'machine_static', 'ghost_hound', 'broken_human', 'error_garden'];
  const tails = new Set();
  for (const family of families) {
    await page.selectOption('#designFamily', family);
    await page.getByRole('button', { name: 'Render Design' }).click();
    const data = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL());
    expect(data.length).toBeGreaterThan(5000);
    tails.add(data.slice(-700));
  }
  expect(tails.size).toBe(5);
});

test('all garment mockups render', async ({ page }) => {
  for (const product of ['hoodie', 'hat', 'beanie', 'cargo', 'mask', 'shirt']) {
    await page.selectOption('#productType', product);
    await page.getByRole('button', { name: 'Render Design' }).click();
    const data = await page.locator('#mockupCanvas').evaluate(c => c.toDataURL());
    expect(data.length).toBeGreaterThan(10000);
  }
});

test('canonical launch capsule auto-maps products to reference families', async ({ page }) => {
  await page.selectOption('#designFamily', 'auto');
  const capsule = [
    ['hat', 'SIGNAL SHADOW'],
    ['mask', 'MACHINE STATIC'],
    ['shirt', 'ERROR GARDEN'],
    ['cargo', 'BROKEN HUMAN'],
    ['beanie', 'GHOST HOUND']
  ];
  for (const [product, family] of capsule) {
    await page.selectOption('#productType', product);
    await expect(page.locator('#resolvedFamily')).toHaveText(family);
    await expect(page.locator('#studioStatus')).toContainText(family);
  }
});

test('signal shadow hat renders four-view reference board', async ({ page }) => {
  await page.selectOption('#productType', 'hat');
  await page.selectOption('#designFamily', 'auto');
  await page.getByRole('button', { name: 'Render Design' }).click();
  await expect(page.locator('#productName')).toHaveValue('SIGNAL SHADOW HAT');
  const data = await page.locator('#mockupCanvas').evaluate(c => c.toDataURL());
  expect(data.length).toBeGreaterThan(12000);
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
  await page.selectOption('#productType', 'hat');
  await page.getByRole('button', { name: 'Render Design' }).click();
  await expect(page.locator('#mockupCanvas')).toBeVisible();
});


test('textile generator reference layout renders all major sections', async ({ page }) => {
  await expect(page.getByText('RAC TEXTILE GENERATOR', { exact: true })).toBeVisible();
  await expect(page.getByText('MOTIF LIBRARY', { exact: true })).toBeVisible();
  await expect(page.getByText('PATTERN FAMILIES', { exact: true })).toBeVisible();
  await expect(page.getByText('SEAMLESS TILE OUTPUT', { exact: true })).toBeVisible();
  await expect(page.getByText('INTEGRATION WITH EXISTING SURROGATE PIPELINE', { exact: true })).toBeVisible();
  await expect(page.locator('.motif-card')).toHaveCount(10);
  await expect(page.locator('.family-card')).toHaveCount(5);
});

test('visual family cards update the conditional generator', async ({ page }) => {
  await page.locator('.family-card.ghost').click();
  await expect(page.locator('#designFamily')).toHaveValue('ghost_hound');
  await expect(page.locator('#resolvedFamily')).toHaveText('GHOST HOUND');
  await expect(page.locator('#studioStatus')).toContainText('GHOST HOUND');
});
