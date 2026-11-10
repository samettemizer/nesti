const isApiCall = (request) => ['fetch', 'xhr'].includes(request.resourceType());

export async function signIn(page, user = { id: 1, name: 'Admin', email: 'admin@example.com' }) {
    await page.route('**/*', (route) => {
        const request = route.request();
        if (!isApiCall(request)) return route.fallback();
        console.log(`[e2e] unstubbed ${request.method()} ${new URL(request.url()).pathname}`);
        return route.fulfill({ status: 404, json: { message: 'Not stubbed in e2e' } });
    });
    await page.addInitScript((u) => {
        localStorage.setItem('auth_token', 'e2e-token');
        localStorage.setItem('auth_user', JSON.stringify(u));
    }, user);
}

// routes: { 'GET /api/users': body } or { 'POST /api/users': { status: 422, json: body } }.
export async function stubApi(page, routes = {}) {
    const entries = Object.entries(routes).map(([key, answer]) => {
        const [method, path] = key.split(' ');
        return { method, path, answer };
    });
    await page.route('**/*', (route) => {
        const request = route.request();
        if (!isApiCall(request)) return route.fallback();
        const pathname = new URL(request.url()).pathname;
        const hit = entries.find((e) => e.method === request.method() && pathname.endsWith(e.path));
        if (!hit) return route.fallback();
        const { status = 200, json } = hit.answer && typeof hit.answer === 'object' && 'json' in hit.answer
            ? hit.answer : { json: hit.answer };
        return route.fulfill({ status, json });
    });
}
