
import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  await page.goto('/login');
  await page.fill('#email', 'demo_hnw@sigmasight.com');
  await page.fill('#password', 'demo12345');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/command-center', { timeout: 30000 });
  await expect(page.getByText('Manage Positions')).toBeVisible();
}

test('manage equity contributions flow', async ({ page }) => {
  page.on('response', async (response) => {
    if (response.url().includes('/equity-changes') && response.status() >= 400) {
      const body = await response.text();
      console.log('[equity-changes error]', response.status(), body);
    }
  });

  await login(page);

  const manageEquityButton = page.getByRole('button', { name: 'Manage Equity' });
  await expect(manageEquityButton).toBeVisible();
  await manageEquityButton.click();

  await expect(page.getByRole('heading', { name: 'Record Equity Change' })).toBeVisible();

  const testAmount = '1234.56';
  await page.fill('#equity-amount', testAmount);
  const today = new Date().toLocaleDateString('en-CA');
  await page.fill('#equity-date', today);
  await page.click('button[type="submit"]');

  await expect(page.getByText('Contribution recorded successfully.', { exact: true })).toBeVisible({ timeout: 20000 });

  await manageEquityButton.click();
  await expect(page.getByRole('heading', { name: 'Record Equity Change' })).toBeVisible({ timeout: 20000 });

  const recentSection = page.locator('section:has(h3:has-text("Recent Activity"))');
  const recentEntry = recentSection.locator('.themed-border', { hasText: '$1,234.56' }).first();
  await expect(recentEntry).toBeVisible();

  const deleteButton = recentEntry.getByRole('button', { name: 'Delete' });
  await deleteButton.click();

  await expect(page.getByText('Equity change deleted successfully.', { exact: true })).toBeVisible({ timeout: 20000 });

  await manageEquityButton.click();
  await expect(page.getByRole('heading', { name: 'Record Equity Change' })).toBeVisible({ timeout: 20000 });
  await expect(recentSection.locator('.themed-border', { hasText: '$1,234.56' })).toHaveCount(0, { timeout: 20000 });
});
