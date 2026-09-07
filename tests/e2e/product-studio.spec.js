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

async function canvasSignature(page, id = '#mockupCanvas') {
  return page.locator(id).evaluate(c => c.toDataURL('image/png'));
}

async function revision(page) {
  return Number(await page.locator('#mockupCanvas').getAttribute('data-render-revision'));
}

test('reference design families render distinct production tiles', async ({ page }) => {
  const families = ['signal_shadow', 'machine_static', 'ghost_hound', 'broken_human', 'error_garden'];
  const tails = new Set();
  for (const family of families) {
    await page.selectOption('#designFamily', family);
    const data = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL());
    expect(data.length).toBeGreaterThan(5000);
    tails.add(data.slice(-700));
  }
  expect(tails.size).toBe(5);
});

test('all garment mockups render distinct dynamic boards', async ({ page }) => {
  const signatures = new Set();
  for (const product of ['hoodie', 'hat', 'beanie', 'cargo', 'mask', 'shirt']) {
    const beforeRevision = await revision(page);
    await page.selectOption('#productType', product);
    await expect.poll(() => revision(page)).toBeGreaterThan(beforeRevision);
    await expect(page.locator('#mockupCanvas')).toHaveAttribute('data-render-product', product);
    const data = await canvasSignature(page);
    expect(data.length).toBeGreaterThan(10000);
    signatures.add(data.slice(-4000));
  }
  expect(signatures.size).toBe(6);
});

test('mockup rebuilds live when seed changes without Generate button', async ({ page }) => {
  const beforeRevision = await revision(page);
  const before = await canvasSignature(page);
  await page.locator('#studioSeed').fill('707');
  await expect(page.locator('#studioSeedValue')).toHaveText('707');
  await expect.poll(() => revision(page)).toBeGreaterThan(beforeRevision);
  await expect(page.locator('#mockupCanvas')).toHaveAttribute('data-render-seed', '707');
  const after = await canvasSignature(page);
  expect(after).not.toBe(before);
});

test('mockup rebuilds live for scale density and distress controls', async ({ page }) => {
  let signature = await canvasSignature(page);
  let rev = await revision(page);
  for (const [id, value] of [['studioScale', '84'], ['studioDensity', '31'], ['studioDistress', '92']]) {
    await page.locator(`#${id}`).fill(value);
    await expect.poll(() => revision(page)).toBeGreaterThan(rev);
    const next = await canvasSignature(page);
    expect(next).not.toBe(signature);
    signature = next;
    rev = await revision(page);
  }
});

test('mockup rebuilds live for family motif and variation state', async ({ page }) => {
  const seen = new Set([await canvasSignature(page)]);
  let rev = await revision(page);

  await page.selectOption('#designFamily', 'ghost_hound');
  await expect.poll(() => revision(page)).toBeGreaterThan(rev);
  await expect(page.locator('#mockupCanvas')).toHaveAttribute('data-render-family', 'ghost_hound');
  seen.add(await canvasSignature(page));
  rev = await revision(page);

  await page.locator('.motif-card[data-motif="rib"]').click();
  await expect.poll(() => revision(page)).toBeGreaterThan(rev);
  seen.add(await canvasSignature(page));
  rev = await revision(page);

  await page.locator('.variation-card[data-variation="high_contrast"]').click();
  await expect.poll(() => revision(page)).toBeGreaterThan(rev);
  await expect(page.locator('#mockupCanvas')).toHaveAttribute('data-render-variation', 'high_contrast');
  seen.add(await canvasSignature(page));

  expect(seen.size).toBe(4);
});

test('canonical launch capsule auto-maps products to reference families', async ({ page }) => {
  await page.selectOption('#designFamily', 'auto');
  const capsule = [['hat', 'SIGNAL SHADOW'],['mask', 'MACHINE STATIC'],['shirt', 'ERROR GARDEN'],['cargo', 'BROKEN HUMAN'],['beanie', 'GHOST HOUND']];
  for (const [product, family] of capsule) {
    await page.selectOption('#productType', product);
    await expect(page.locator('#resolvedFamily')).toHaveText(family);
    await expect(page.locator('#studioStatus')).toContainText(family);
  }
});

test('signal shadow hat renders four-view reference board', async ({ page }) => {
  await page.selectOption('#productType', 'hat');
  await page.selectOption('#designFamily', 'auto');
  await expect(page.locator('#productName')).toHaveValue('SIGNAL SHADOW HAT');
  const data = await canvasSignature(page);
  expect(data.length).toBeGreaterThan(12000);
});

test('studio controls update deterministic variation', async ({ page }) => {
  const before = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL().slice(-900));
  await page.locator('#studioSeed').fill('707');
  await expect(page.locator('#studioSeedValue')).toHaveText('707');
  await expect(page.locator('#studioStatus')).toContainText('SEED 707');
  const after = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL().slice(-900));
  expect(after).not.toBe(before);
});

test('reference board exports true 4096px output and manifest remains non-empty', async ({ page }) => {
  const boardWait = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export Reference Board PNG' }).click();
  const boardDownload = await boardWait;
  const boardPath = await boardDownload.path();
  const png = fs.readFileSync(boardPath);
  expect(png.length).toBeGreaterThan(1000);
  expect(png.readUInt32BE(16)).toBe(4096);
  expect(png.readUInt32BE(20)).toBe(5119);

  const manifestWait = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export Production Manifest' }).click();
  const manifestDownload = await manifestWait;
  const manifestPath = await manifestDownload.path();
  expect(fs.statSync(manifestPath).size).toBeGreaterThan(200);
});

test('product studio remains usable on mobile', async ({ page }) => {
  await expect(page.locator('.studio-grid')).toBeVisible();
  const rev = await revision(page);
  await page.selectOption('#productType', 'hat');
  await expect.poll(() => revision(page)).toBeGreaterThan(rev);
  await expect(page.locator('#mockupCanvas')).toBeVisible();
});

test('visual family cards update the conditional generator', async ({ page }) => {
  const rev = await revision(page);
  await page.locator('.family-card.ghost').click();
  await expect(page.locator('#designFamily')).toHaveValue('ghost_hound');
  await expect(page.locator('#resolvedFamily')).toHaveText('GHOST HOUND');
  await expect.poll(() => revision(page)).toBeGreaterThan(rev);
});

test('Next Variation rebuilds the board', async ({ page }) => {
  const seed = Number(await page.locator('#studioSeed').inputValue());
  const before = await canvasSignature(page);
  const rev = await revision(page);
  await page.getByRole('button', { name: 'Next Variation' }).click();
  expect(Number(await page.locator('#studioSeed').inputValue())).not.toBe(seed);
  await expect.poll(() => revision(page)).toBeGreaterThan(rev);
  expect(await canvasSignature(page)).not.toBe(before);
});

test('motif library features are selectable and change generated textile and mockup', async ({ page }) => {
  const beforeTile = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL().slice(-1200));
  const beforeBoard = await canvasSignature(page);
  const motif = page.locator('.motif-card[data-motif="rib"]');
  await motif.click();
  await expect(motif).toHaveClass(/selected/);
  const afterTile = await page.locator('#studioPatternCanvas').evaluate(c => c.toDataURL().slice(-1200));
  expect(afterTile).not.toBe(beforeTile);
  expect(await canvasSignature(page)).not.toBe(beforeBoard);
});

test('manifest records selected stylized motif features', async ({ page }) => {
  await page.locator('.motif-card[data-motif="canine_eye"]').click();
  await page.locator('.motif-card[data-motif="slash"]').click();
  const wait = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export Production Manifest' }).click();
  const download = await wait;
  const path = await download.path();
  const manifest = JSON.parse(fs.readFileSync(path, 'utf8'));
  expect(manifest.design.feature_motifs).toEqual(expect.arrayContaining(['canine_eye', 'slash']));
  expect(manifest.outputs.reference_board_px).toEqual([4096, 5119]);
  expect(manifest.outputs.preview_board_px).toEqual([1122, 1402]);
});

test('variation preset buttons each alter generator and mockup state', async ({ page }) => {
  const seen = new Set();
  for (const preset of ['original', 'high_contrast', 'desaturated', 'alt_palette', 'scale_plus']) {
    const button = page.locator(`.variation-card[data-variation="${preset}"]`);
    await button.click();
    await expect(button).toHaveClass(/selected/);
    await expect(page.locator('#mockupCanvas')).toHaveAttribute('data-render-variation', preset);
    seen.add((await canvasSignature(page)).slice(-4000));
  }
  expect(seen.size).toBeGreaterThanOrEqual(4);
});

test('4096 tile export button produces a non-empty download', async ({ page }) => {
  const wait = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export 4096px POD Tile' }).click();
  const download = await wait;
  const path = await download.path();
  expect(fs.statSync(path).size).toBeGreaterThan(1000);
});

test('obsolete low-resolution showcase source is absent', async ({ page }) => {
  await expect(page.locator('.showcase-source-section')).toHaveCount(0);
  await expect(page.locator('#showcaseReference')).toHaveCount(0);
  await expect(page.locator('#useShowcaseSource')).toHaveCount(0);
  await expect(page.locator('#showcaseRegion')).toHaveCount(0);
  await expect(page.locator('#showcaseStrength')).toHaveCount(0);
  const scripts = await page.locator('script[src]').evaluateAll(nodes => nodes.map(n => n.getAttribute('src')));
  expect(scripts).not.toContain('showcase-asset.js');
});


test('reference match mode is default and reports deterministic fidelity', async ({ page }) => {
  await expect(page.locator('#generationMode')).toHaveValue('reference');
  const first = await page.locator('#referenceProfileStatus').textContent();
  await page.evaluate(() => RACStudio.renderAll());
  const second = await page.locator('#referenceProfileStatus').textContent();
  expect(first).toBe(second);
  expect(second).toMatch(/FIDELITY \d+\.\d\/100/);
});

test('find best match preserves or improves reference fidelity', async ({ page }) => {
  const score = async () => Number((await page.locator('#referenceProfileStatus').textContent()).match(/FIDELITY (\d+\.\d)/)[1]);
  const before = await score();
  await page.getByRole('button', { name: 'Find Best Match' }).click();
  await expect.poll(score).toBeGreaterThanOrEqual(before);
});

test('reference profile clamps effective controls deterministically', async ({ page }) => {
  const result = await page.evaluate(() => {
    const r = RACStyleProfiles.resolveProfile({family:'signal_shadow',product:'hat',mode:'reference',controls:{scale:100,density:1,distress:1}});
    return {scale:r.scale,density:r.density,distress:r.distress};
  });
  expect(result).toEqual({scale:68,density:58,distress:60});
});
