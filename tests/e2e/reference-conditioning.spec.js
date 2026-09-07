const { test, expect } = require('@playwright/test');

const REFERENCE_SVG = Buffer.from(`
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">
  <rect width="512" height="512" fill="#080808"/>
  <rect x="32" y="48" width="210" height="70" fill="#d8ccb6"/>
  <rect x="270" y="28" width="55" height="330" fill="#155bd8"/>
  <path d="M40 430 L220 150 L315 325 L475 70" fill="none" stroke="#e7df16" stroke-width="36"/>
  <ellipse cx="185" cy="270" rx="110" ry="62" fill="none" stroke="#d98ca4" stroke-width="20"/>
</svg>`);

const LOW_RES_SVG = Buffer.from(`
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">
  <rect width="128" height="128" fill="#080808"/>
</svg>`);

test.beforeEach(async ({ page }) => {
  await page.goto('product-studio.html');
  await expect(page.locator('#studioStatus')).toContainText('READY');
});

test('reference conditioning analyzes local source and rebuilds the mockup', async ({ page }) => {
  const revisionBefore = Number(await page.locator('#mockupCanvas').getAttribute('data-render-revision'));
  await page.locator('#referenceInput').setInputFiles({
    name: 'approved-reference.svg',
    mimeType: 'image/svg+xml',
    buffer: REFERENCE_SVG,
  });

  await page.getByRole('button', { name: 'Analyze', exact: true }).click();
  await expect(page.locator('#referenceStatus')).toContainText('PROFILE READY');
  await expect(page.locator('.reference-swatch')).toHaveCount(7);

  const profile = await page.evaluate(() => window.RACReferenceConditioner.getProfile());
  expect(profile.schema_version).toBe('1.0');
  expect(profile.mode).toBe('scalar_style_conditioning');
  expect(profile.source_count).toBe(1);
  expect(profile.source_sha256[0]).toMatch(/^[0-9a-f]{64}$/);
  expect(profile.combined_sha256).toMatch(/^[0-9a-f]{64}$/);
  expect(profile.source_pixels_used_in_output).toBe(false);
  expect(profile.evidence_scope).toBe('design_reference_only');

  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  await expect(page.locator('#referenceStatus')).toHaveText('REFERENCE APPLIED');
  await expect.poll(async () => Number(await page.locator('#mockupCanvas').getAttribute('data-render-revision')))
    .toBeGreaterThan(revisionBefore);

  const snapshot = await page.evaluate(() => window.RACStudioBridge.snapshot());
  expect(snapshot.reference_source_mode).toBe('scalar_style_conditioning');
  expect(snapshot.reference_profile.source_pixels_used_in_output).toBe(false);
});

test('reference conditioner rejects low-resolution analysis sources', async ({ page }) => {
  await page.locator('#referenceInput').setInputFiles({
    name: 'low-res.svg',
    mimeType: 'image/svg+xml',
    buffer: LOW_RES_SVG,
  });
  await page.getByRole('button', { name: 'Analyze', exact: true }).click();
  await expect(page.locator('#referenceStatus')).toContainText('below the 256px reference-analysis minimum');
  const profile = await page.evaluate(() => window.RACReferenceConditioner.getProfile());
  expect(profile).toBeNull();
});

test('obsolete showcase sampling path remains absent', async ({ page }) => {
  await expect(page.locator('#showcaseReference')).toHaveCount(0);
  await expect(page.locator('#useShowcaseSource')).toHaveCount(0);
  const bridgeSource = await page.evaluate(async () => (await fetch('studio-bridge.js')).text());
  expect(bridgeSource).not.toContain('vectorShowcase');
  expect(bridgeSource).not.toContain('showcaseReference');
  expect(bridgeSource).not.toContain('use_existing_showcase');
});
