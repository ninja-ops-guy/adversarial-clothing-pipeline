const { test, expect } = require('@playwright/test');

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('capture-lab.html');
  await expect(page.getByText('RAC CAPTURE LAB', { exact: true })).toBeVisible();
  page.__errors = errors;
});

test.afterEach(async ({ page }) => {
  expect(page.__errors || []).toEqual([]);
});

test('capture lab exposes SOP sequence and evidence classes', async ({ page }) => {
  await expect(page.locator('.sop-step')).toHaveCount(7);
  await expect(page.locator('#evidenceClass')).toHaveValue('printed_flat_prototype');
  await expect(page.locator('#controlCount')).toContainText('0 stills');
  await expect(page.locator('#candidateCount')).toContainText('0 stills');
});

test('freezing session locks experiment metadata and enables scientific workflow', async ({ page }) => {
  await page.locator('#candidateId').fill('RAC-TEST-CANDIDATE');
  await page.locator('#candidateSha').fill('a'.repeat(64));
  await page.getByRole('button', { name: 'Freeze Session Manifest' }).click();
  await expect(page.locator('#instrumentStatus')).toContainText('FROZEN');
  await expect(page.locator('#experimentId')).toBeDisabled();
  await expect(page.locator('#candidateSha')).toBeDisabled();
  await expect(page.locator('.sop-step').nth(0)).toHaveClass(/done/);
  await expect(page.locator('.sop-step').nth(1)).toHaveClass(/active/);
});

test('analysis manifest defaults to identity matching disabled', async ({ page }) => {
  const text = await page.locator('#modelManifest').inputValue();
  const manifest = JSON.parse(text);
  expect(manifest.identity_mode).toBe('disabled');
  expect(manifest.models).toEqual([]);
});

test('synthetic dry-run evidence class remains explicit', async ({ page }) => {
  await page.selectOption('#evidenceClass', 'synthetic_pipeline_validation_only');
  await page.locator('#candidateSha').fill('b'.repeat(64));
  await page.getByRole('button', { name: 'Freeze Session Manifest' }).click();
  const state = await page.evaluate(() => window.RACCaptureLab.getState());
  expect(state.frozen.evidence_class).toBe('synthetic_pipeline_validation_only');
});


test('frozen ensemble includes deterministic motion sampling contract', async ({ page }) => {
  const manifest = JSON.parse(await page.locator('#modelManifest').inputValue());
  expect(manifest.motion_sampling).toEqual({
    fps: 2.0,
    max_frames: 120,
    aggregation: 'sequence_fraction'
  });
  await page.selectOption('#ensemblePreset', 'heldout');
  const heldout = JSON.parse(await page.locator('#modelManifest').inputValue());
  expect(heldout.models).toEqual(['fasterrcnn_resnet50_fpn_v2', 'maskrcnn_resnet50_fpn_v2']);
  expect(heldout.motion_sampling.fps).toBe(2.0);
  expect(heldout.motion_sampling.sequence_detection_threshold).toBe(0.5);
  expect(heldout.identity_mode).toBe('disabled');
});


test('session setup exposes Research OS lineage fields', async ({ page }) => {
  await expect(page.locator('#experimentId')).toHaveValue('RAC-EXP-2026-001');
  await expect(page.locator('#hypothesisId')).toHaveValue('RQ-P1-CAPTURE-001');
  await expect(page.locator('#generationId')).toBeVisible();
  await expect(page.locator('#generationSha')).toBeVisible();
});
