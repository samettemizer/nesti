const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export class ApiError extends Error {
    constructor(status, message, errors = {}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.errors = errors;
    }
}

async function request(method, path, body) {
    const headers = { Accept: 'application/json', 'Content-Type': 'application/json' };
    const token = localStorage.getItem('auth_token');
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await fetch(BASE + '/api' + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body)
    });

    if (response.status === 204) return null;

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        window.dispatchEvent(new Event('auth:expired'));
    }
    if (!response.ok) {
        throw new ApiError(response.status, data.message ?? response.statusText, data.errors ?? {});
    }
    return data;
}

export const api = {
    get: (path) => request('GET', path),
    post: (path, body) => request('POST', path, body)
};
