
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import http from 'http';

async function waitForPort(port, timeout = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get({ hostname: 'localhost', port, path: '/', timeout: 5000 }, (res) => {
          res.resume();
          resolve();
        });
        req.on('error', reject);
        req.on('timeout', () => {
          req.destroy();
          reject(new Error('timeout'));
        });
      });
      return;
    } catch (err) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  throw new Error(`Timed out waiting for port ${port}`);
}

function startProcess(command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    shell: true,
    stdio: 'inherit',
  });
  return child;
}

async function runTest() {
  const backend = startProcess('uv', ['run', 'python', 'run.py'], '../backend');
  const frontend = startProcess('npm', ['run', 'dev'], '.');

  try {
    await Promise.all([
      waitForPort(8000),
      waitForPort(3005),
    ]);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('http://localhost:3005/login');
    await page.fill('input[name="email"]', 'demo_hnw@sigmasight.com');
    await page.fill('input[name="password"]', 'demo12345');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/command-center', { timeout: 30000 });

    const manageEquityButton = page.getByRole('button', { name: 'Manage Equity' });
    await manageEquityButton.waitFor({ state: 'visible', timeout: 20000 });
    await manageEquityButton.click();

    await page.getByRole('heading', { name: 'Record Equity Change' }).waitFor({ state: 'visible', timeout: 20000 });

    const testAmount = '1234.56';
    await page.fill('#equity-amount', testAmount);
    const today = new Date().toISOString().split('T')[0];
    await page.fill('#equity-date', today);
    await page.click('button[type="submit"]');

    await page.getByText('Contribution recorded successfully.', { exact: true }).waitFor({ state: 'visible', timeout: 30000 });

    const netFlowCard = page.getByText('Net Capital Flow (30d)').locator('..');
    await netFlowCard.waitFor({ state: 'visible', timeout: 20000 });
    const netFlowText = await netFlowCard.innerText();

    const recentEntry = page.locator('.themed-border', { hasText: '$1,234.56' }).first();
    await recentEntry.waitFor({ state: 'visible', timeout: 20000 });

    const deleteButton = recentEntry.getByRole('button', { name: 'Delete' });
    if (await deleteButton.isVisible()) {
      await deleteButton.click();
      await page.waitForTimeout(1000);
    }

    await browser.close();

    console.log('Playwright equity flow test completed successfully.');
    console.log(`Net Flow Card Text: ${netFlowText}`);
  } catch (error) {
    console.error('Playwright equity flow test failed:', error);
    process.exitCode = 1;
  } finally {
    frontend.kill();
    backend.kill();
  }
}

runTest();
