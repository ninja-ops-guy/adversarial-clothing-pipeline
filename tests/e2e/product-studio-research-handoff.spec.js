const { test, expect } = require('@playwright/test');

test('P0 family survives Product Studio to Production Mapper state handoff', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('product-studio.html');
  await expect(page.locator('.family-card.p0-research')).toHaveCount(8);
  await page.selectOption('#designFamily', 'swapped_landmarks');
  await page.evaluate(() => RACStudioBridge.snapshot());

  await page.goto('production-studio.html');
  await expect(page.locator('#productionStatus')).not.toContainText('INITIALIZING');
  await expect.poll(async () => page.locator('#family option').count()).toBeGreaterThanOrEqual(13);
  await page.getByRole('button', { name: 'Load Current Product Studio Design' }).click();
  await expect(page.locator('#family')).toHaveValue('swapped_landmarks');
  await expect(page.locator('#researchCandidateImport')).toBeVisible();
  await expect(page.locator('#researchCandidateStatus')).toContainText('NO CANDIDATE LOADED');

  expect(errors).toEqual([]);
});
