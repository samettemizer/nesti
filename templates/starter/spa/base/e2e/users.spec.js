import { expect, test } from '@playwright/test';
import { signIn } from './support/session.js';

test('the users table shows the API rows', async ({ page }) => {
    await signIn(page);
    await page.route('**/api/users*', (route) =>
        route.fulfill({
            json: {
                data: [
                    { id: 1, name: 'Admin', email: 'admin@example.com', created_at: '2026-01-01T00:00:00Z' },
                    { id: 2, name: 'Ann', email: 'ann@example.com', created_at: '2026-01-02T00:00:00Z' }
                ],
                links: {},
                meta: { total: 2 }
            }
        })
    );
    await page.goto('/users');
    await expect(page.getByText('admin@example.com')).toBeVisible();
    await expect(page.getByText('ann@example.com')).toBeVisible();
});
