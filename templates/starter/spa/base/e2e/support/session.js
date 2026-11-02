export async function signIn(page, user = { id: 1, name: 'Admin', email: 'admin@example.com' }) {
    await page.addInitScript((u) => {
        localStorage.setItem('auth_token', 'e2e-token');
        localStorage.setItem('auth_user', JSON.stringify(u));
    }, user);
}
