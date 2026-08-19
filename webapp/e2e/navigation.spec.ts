import { expect, test } from '@playwright/test';

test('dashboard renders KPIs and backend health', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('dashboard')).toBeVisible();
  await expect(page.getByTestId('backend-dot')).toBeVisible();
  await expect(page.getByTestId('kpi-server')).toBeVisible();
  await expect(page.getByTestId('kpi-robot')).toBeVisible();
});

test('nav walk visits all sidebar pages', async ({ page }) => {
  await page.goto('/');
  const nav = [
    ['/#/tools', 'MCP Tools'],
    ['/#/inbox', 'Activity Inbox'],
    ['/#/skills', 'Supervisor Skills'],
    ['/#/logs', 'Event Logs'],
    ['/#/apps', 'Fleet Apps'],
    ['/#/settings', 'Settings'],
    ['/#/help', 'Help'],
  ];
  for (const [path, title] of nav) {
    await page.goto(path);
    await expect(page.getByTestId('dashboard')).toBeVisible();
    await expect(page.locator('h2').first()).toContainText(title);
  }
});

test('settings exposes LLM provider + model selects', async ({ page }) => {
  await page.goto('/#/settings');
  await expect(page.getByTestId('llm-provider-select')).toBeVisible();
});
