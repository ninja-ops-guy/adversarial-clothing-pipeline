const { test, expect } = require('@playwright/test');

const landingUrl = process.env.BASE_URL || '/landing.html';

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(landingUrl);
  page.__landingErrors = errors;
});

test.afterEach(async ({ page }) => {
  expect(page.__landingErrors || []).toEqual([]);
});

test('landing page exposes RAC research posture and platform surfaces', async ({ page }) => {
  await expect(page.getByRole('heading', { name: /Machine-optimized textiles/i })).toBeVisible();
  await expect(page.getByText('OPEN / NOT EXECUTED')).toBeVisible();
  await expect(page.getByText('NOT SUPPORTED', { exact: true })).toBeVisible();
  await expect(page.getByText('144', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: /ENTER PATTERN LAB/i })).toHaveAttribute('href', './pattern-lab.html');
  await expect(page.getByRole('link', { name: /OPEN RESEARCH CONSOLE/i })).toHaveAttribute('href', './research_console/index.html');
});

test('evidence ladder preserves digital, physical, and manufacturing boundaries', async ({ page }) => {
  await page.locator('#evidence').scrollIntoViewIfNeeded();
  for (const state of ['RAC-D0','RAC-D1','RAC-D2','RAC-P1','RAC-P2','RAC-M1','RAC-M2']) {
    await expect(page.getByText(state, { exact: true })).toBeVisible();
  }
  await expect(page.getByText(/Digital evidence may never satisfy a physical or manufacturing state/)).toBeVisible();
});

test('interactive system cards open an explainer without console errors', async ({ page }) => {
  await page.locator('[data-detail="certification"]').click();
  const dialog = page.locator('#detailDialog');
  await expect(dialog).toBeVisible();
  await expect(page.locator('#detailTitle')).toHaveText('Certification & evidence plane');
  await expect(page.locator('#detailBoundary')).toContainText('internal evidence framework');
  await page.getByRole('button', { name: /Close detail/i }).click();
  await expect(dialog).not.toBeVisible();
});

test('landing page remains usable on a mobile viewport', async ({ page }) => {
  await expect(page.locator('.hero-copy')).toBeVisible();
  await expect(page.locator('.specimen-panel')).toBeVisible();
  await page.locator('#platform').scrollIntoViewIfNeeded();
  await expect(page.getByRole('link', { name: /Pattern Lab/i }).last()).toBeVisible();
  await expect(page.getByRole('link', { name: /Research Console/i }).last()).toBeVisible();
});
