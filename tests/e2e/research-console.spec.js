const { test, expect } = require('@playwright/test');

test('research console links apps and reflects published experiment state', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('research_console/index.html');
  await expect(page.getByRole('heading', { name: 'RAC Research Console' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Pattern Lab/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /Product Studio/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /Production Mapper/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /Capture Lab/ })).toBeVisible();
  await expect(page.locator('#experimentStatus')).toContainText('RAC-PER-D2-0004');
  await expect(page.locator('#experimentStatus')).toContainText('FAIL');
  await expect(page.locator('#experimentStatus')).toContainText('RAC-D0');
  await expect(page.getByText('Pass 1 · Governance Core')).toBeVisible();
  await expect(page.getByText('Pattern Genome v1')).toBeVisible();
  expect(errors).toEqual([]);
});
