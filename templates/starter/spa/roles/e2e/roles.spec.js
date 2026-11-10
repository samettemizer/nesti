import { expect, test } from '@playwright/test';
import { signIn } from './support/session.js';

test('roles and permissions come from the API', async ({ page }) => {
    await signIn(page);
    await page.route('**/api/roles', (route) =>
        route.fulfill({ json: { data: [{ id: 1, name: 'admin', guard_name: 'web', permissions: ['users.view', 'roles.view'] }] } })
    );
    await page.route('**/api/permissions', (route) =>
        route.fulfill({ json: { data: [{ id: 1, name: 'users.view', guard_name: 'web' }, { id: 2, name: 'roles.view', guard_name: 'web' }] } })
    );
    await page.goto('/roles');
    await expect(page.getByRole('cell', { name: 'admin', exact: true })).toBeVisible();
    await expect(page.locator('.p-tag', { hasText: 'users.view' })).toBeVisible();
});
