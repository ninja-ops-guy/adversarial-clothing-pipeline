const { test, expect } = require('@playwright/test');

const P0 = [
  'hyperface_like',
  'dazzle_surgical_lines',
  'key_feature_blackout',
  'saliency_eye_attack',
  'adversarial_patch',
  'swapped_landmarks',
  'landmark_noise',
  'feature_collage',
];
const CANONICAL = ['signal_shadow', 'machine_static', 'ghost_hound', 'broken_human', 'error_garden'];
const TINY_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGMUUHBgYGBgYmBgYGBgAAAFOgB0XtSh0QAAAABJRU5ErkJggg==',
  'base64'
);

test('Product Studio exposes complete implemented family inventory without promoting deferred families', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('product-studio.html');
  await expect(page.locator('.family-card.p0-research')).toHaveCount(8);

  const catalog = await page.evaluate(() => ({
    implementedFamilyIds: RACStudioResearchCatalog.implementedFamilyIds,
    p0Ids: RACStudioResearchCatalog.p0Families.map(x => x.id),
    deferred: RACStudioResearchCatalog.deferred,
  }));
  expect(catalog.implementedFamilyIds).toEqual([...CANONICAL, ...P0]);
  expect(catalog.p0Ids).toEqual(P0);
  expect(catalog.deferred).toEqual({ p1: 5, p2: 23, p3_refused: ['bad_words', 'web_attack_strings'] });

  const options = await page.locator('#designFamily option').evaluateAll(nodes => nodes.map(node => node.value));
  for (const family of [...CANONICAL, ...P0]) expect(options).toContain(family);
  expect(options).not.toContain('bad_words');
  expect(options).not.toContain('web_attack_strings');
  expect(errors).toEqual([]);
});

test('P0 selection requires a governed candidate import and preserves its provenance metadata', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('product-studio.html');
  await expect(page.locator('.family-card.p0-research')).toHaveCount(8);

  await page.selectOption('#designFamily', 'hyperface_like');
  await expect(page.locator('#researchCandidateImport')).toBeVisible();
  await expect(page.locator('#findBestMatchBtn')).toBeDisabled();
  await expect(page.locator('#referenceProfileStatus')).toContainText('GOVERNED CANDIDATE REQUIRED');

  await page.locator('#researchCandidateFile').setInputFiles({
    name: 'governed-candidate.png',
    mimeType: 'image/png',
    buffer: TINY_PNG,
  });
  await expect(page.locator('#researchCandidateStatus')).toContainText('LOADED');
  await expect(page.locator('#mockupCanvas')).toHaveAttribute('data-frozen-tile', 'true');

  const metadata = await page.evaluate(() => RACStudio.getFrozenTileMetadata());
  expect(metadata.research_family).toBe('hyperface_like');
  expect(metadata.generator).toBe('HyperfaceLikeGenerator');
  expect(metadata.sha256).toMatch(/^[0-9a-f]{64}$/);
  expect(metadata.evidence_scope).toBe('imported_governed_candidate_preview_not_physical_efficacy');
  expect(errors).toEqual([]);
});

test('Production Mapper accepts the same P0 catalog and disables inappropriate reference-fidelity ranking', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('production-studio.html');
  await expect(page.locator('#productionStatus')).not.toContainText('INITIALIZING');
  await expect.poll(async () => page.locator('#family option').count()).toBeGreaterThanOrEqual(13);

  await page.selectOption('#family', 'feature_collage');
  await expect(page.locator('#researchCandidateImport')).toBeVisible();
  await expect(page.locator('#batchRankingMode')).toHaveValue('visual_proxy');
  await expect(page.locator('#batchRankingMode option[value="reference_fidelity"]')).toBeDisabled();

  await page.locator('#researchCandidateFile').setInputFiles({
    name: 'governed-candidate.png',
    mimeType: 'image/png',
    buffer: TINY_PNG,
  });
  await expect(page.locator('#researchCandidateStatus')).toContainText('LOADED');
  const metadata = await page.evaluate(() => RACStudioResearchCatalog.getImportedMetadata());
  expect(metadata.research_family).toBe('feature_collage');
  expect(metadata.sha256).toMatch(/^[0-9a-f]{64}$/);
  expect(errors).toEqual([]);
});

test('Product Studio only shows functional mode controls and correctly labels downstream panel-pack export', async ({ page }) => {
  await page.goto('product-studio.html');
  await expect(page.locator('.mode-tabs')).toHaveCount(0);
  await expect(page.locator('.output-file')).toContainText(['pattern_tile.png', 'reference_board.png', 'pattern_metadata.json', 'panel_pack.zip']);
  await expect(page.getByText('via Production Mapper')).toBeVisible();
});
