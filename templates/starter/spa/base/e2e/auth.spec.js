import { expect, test } from '@playwright/test';

test('an unauthenticated visit lands on the login page', async ({ page }) => {
    await page.goto('/users');
    await expect(page).toHaveURL(/\/auth\/login\?redirect=/);
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
});

test('signing in opens the dashboard with the user in the topbar', async ({ page }) => {
    await page.route('**/api/login', (route) =>
        route.fulfill({ json: { token: 'e2e-token', user: { id: 1, name: 'Admin', email: 'admin@example.com' } } })
    );
    await page.goto('/auth/login');
    await page.getByLabel('Email').fill('admin@example.com');
    await page.locator('#password').fill('password');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId('topbar-user')).toHaveText('Admin');
});

test('rejected credentials show the error', async ({ page }) => {
    await page.route('**/api/login', (route) =>
        route.fulfill({ status: 422, json: { message: 'Invalid.', errors: { email: ['These credentials do not match our records.'] } } })
    );
    await page.goto('/auth/login');
    await page.getByLabel('Email').fill('admin@example.com');
    await page.locator('#password').fill('wrong');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByText('These credentials do not match our records.')).toBeVisible();
});
