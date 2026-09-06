const { test, expect } = require('@playwright/test');

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(process.env.BASE_URL || '/');
  await expect(page.locator('#previewCanvas')).toBeVisible();
  await expect(page.locator('#historyCount')).not.toHaveText('0');
  page.__errors = errors;
});

test.afterEach(async ({ page }) => {
  expect(page.__errors || []).toEqual([]);
});

test('all pattern generators render and change the canvas', async ({ page }) => {
  const types = ['noise','geometric','organic','checkered','striped','circular','cellular','perlin'];
  const hashes = new Set();
  for (const type of types) {
    await page.selectOption('#patternType', type);
    await page.waitForTimeout(180);
    const data = await page.locator('#previewCanvas').evaluate(c => c.toDataURL());
    expect(data.length).toBeGreaterThan(1000);
    hashes.add(data.slice(-500));
  }
  expect(hashes.size).toBeGreaterThan(4);
});

test('parameter controls, palettes, symmetry and high contrast execute', async ({ page }) => {
  await page.locator('#patternScale').fill('88');
  await page.locator('#colorVariance').fill('33');
  await page.locator('#edgeIntensity').fill('77');
  await page.locator('#symmetry').fill('3');
  await page.selectOption('#colorPalette', 'neon');
  await page.locator('#contrastToggle').click();
  await page.getByRole('button', { name: /Generate Pattern/ }).click();
  await page.waitForTimeout(180);
  await expect(page.locator('#patternScaleValue')).toHaveText('88');
  await expect(page.locator('#colorVarianceValue')).toHaveText('33');
  await expect(page.locator('#edgeIntensityValue')).toHaveText('77');
  await expect(page.locator('#symmetryValue')).toHaveText('3');
});

test('simulation works across every pose, fabric and lighting option', async ({ page }) => {
  await page.getByText('Simulation', { exact: true }).click();
  const poses = ['standing','walking','sitting','arms_raised'];
  const fabrics = ['cotton','polyester','silk','denim'];
  const lights = ['indoor','outdoor','low_light','direct_sun'];
  for (const p of poses) {
    await page.selectOption('#poseSelect', p);
    for (const f of fabrics) {
      await page.selectOption('#fabricType', f);
      for (const l of lights) {
        await page.selectOption('#lightingSelect', l);
        const pixel = await page.locator('#simulationCanvas').evaluate(c => {
          const d=c.getContext('2d').getImageData(256,256,1,1).data; return [...d];
        });
        expect(pixel[3]).toBe(255);
      }
    }
  }
  await page.locator('#warpIntensity').fill('80');
  await expect(page.locator('#warpIntensityValue')).toHaveText('80');
});

test('analysis produces visible heuristic metrics and charts', async ({ page }) => {
  await page.getByText('Analysis', { exact: true }).click();
  for (const id of ['yoloRate','detrRate','rcnnRate','ssdRate']) {
    await expect(page.locator('#'+id)).toHaveText(/\d+%/);
  }
  for (const id of ['frequencyCanvas','colorCanvas']) {
    const nonEmpty = await page.locator('#'+id).evaluate(c => {
      const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
      return Array.from(d).some(v => v !== 0);
    });
    expect(nonEmpty).toBeTruthy();
  }
});

test('gallery, selection, comparison and reset work', async ({ page }) => {
  await page.getByRole('button', { name: /Generate Pattern/ }).click();
  await page.waitForTimeout(180);
  await page.getByText('Gallery', { exact: true }).click();
  await expect(page.locator('.pattern-thumb')).toHaveCount(2);
  await page.locator('.pattern-thumb').first().click();
  await expect(page.locator('.pattern-thumb.selected')).toHaveCount(1);
  await page.getByRole('button', { name: /Compare Selected/ }).click();
  await expect(page.locator('#logConsole')).toContainText('Comparison logged to console');
  await page.getByRole('button', { name: /Reset/ }).click();
  await expect(page.locator('#historyCount')).toHaveText('0');
  await expect(page.locator('.pattern-thumb')).toHaveCount(0);
});

test('randomize and heuristic seed search complete with a real generated result', async ({ page }) => {
  await page.getByRole('button', { name: /Randomize Parameters/ }).click();
  await page.waitForTimeout(220);
  await expect(page.locator('#logConsole')).toContainText('Parameters randomized');
  await page.getByRole('button', { name: /Quick Optimize/ }).click();
  await expect(page.locator('#logConsole')).toContainText(/Heuristic seed search complete/,{timeout:15000});
  await expect(page.locator('#transferRate')).toHaveText(/\d+%/);
});

test('animation advances seeds and can stop', async ({ page }) => {
  const before = Number(await page.locator('#seed').inputValue());
  await page.locator('#animationToggle').click();
  await page.waitForTimeout(1200);
  await page.locator('#animationToggle').click();
  const after = Number(await page.locator('#seed').inputValue());
  expect(after).not.toBe(before);
  const stopped = after;
  await page.waitForTimeout(800);
  expect(Number(await page.locator('#seed').inputValue())).toBe(stopped);
});

test('PNG, JSON, SVG and full config exports download non-empty files', async ({ page }) => {
  const actions = [
    () => page.getByRole('button', { name: /Export as PNG/ }).click(),
    () => page.getByRole('button', { name: /Export Config \(JSON\)/ }).click(),
    () => page.getByRole('button', { name: /Export as SVG/ }).click(),
    () => page.locator('.header-actions').getByRole('button', { name: /Export Config/ }).click()
  ];
  for (const action of actions) {
    const dl = page.waitForEvent('download');
    await action();
    const download = await dl;
    expect(download.suggestedFilename()).toMatch(/\.(png|json|svg)$/);
    const path = await download.path();
    const fs = require('fs');
    expect(fs.statSync(path).size).toBeGreaterThan(100);
  }
});

test('mobile viewport remains usable', async ({ page }) => {
  await expect(page.locator('.main-container')).toBeVisible();
  await page.getByText('Gallery', { exact: true }).click();
  await expect(page.locator('#gallery')).toBeVisible();
  await page.getByText('Preview', { exact: true }).click();
  await expect(page.locator('#previewCanvas')).toBeVisible();
});


test('measured benchmark imports are explicitly labeled and provenance is displayed', async ({ page }) => {
  await page.getByText('Analysis', { exact: true }).click();
  const payload = {
    experiment_id: 'EXP-001',
    config: { heldout_models: ['DET-HO-001'] },
    summary: {
      heldout: { baseline_detection_rate: 1.0, candidate_detection_rate: 0.4 },
      invalid_condition_fraction: 0.0
    }
  };
  await page.locator('#measuredResultsFile').setInputFiles({
    name: 'benchmark.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(payload))
  });
  await expect(page.locator('#measuredEvidence')).toContainText('INTERNALLY MEASURED');
  await expect(page.locator('#measuredEvidence')).toContainText('EXP-001');
  await expect(page.locator('#measuredEvidence')).toContainText('DET-HO-001');
});
