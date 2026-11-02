import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/service/api';

function reply(status, body) {
    return vi.fn().mockResolvedValue({
        status,
        ok: status >= 200 && status < 300,
        statusText: 'status',
        json: () => Promise.resolve(body)
    });
}

describe('api', () => {
    beforeEach(() => localStorage.setItem('auth_token', 'secret'));
    afterEach(() => {
        localStorage.clear();
        vi.unstubAllGlobals();
    });

    it('sends the bearer token', async () => {
        const fetch = reply(200, { data: [] });
        vi.stubGlobal('fetch', fetch);
        await api.get('/users');
        expect(fetch).toHaveBeenCalledWith('/api/users', expect.objectContaining({ method: 'GET' }));
        expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer secret');
    });

    it('clears storage and dispatches auth:expired on 401', async () => {
        localStorage.setItem('auth_user', '{}');
        vi.stubGlobal('fetch', reply(401, { message: 'Unauthenticated.' }));
        const expired = vi.fn();
        window.addEventListener('auth:expired', expired);
        await expect(api.get('/users')).rejects.toBeInstanceOf(ApiError);
        window.removeEventListener('auth:expired', expired);
        expect(expired).toHaveBeenCalledOnce();
        expect(localStorage.getItem('auth_token')).toBeNull();
        expect(localStorage.getItem('auth_user')).toBeNull();
    });

    it('throws ApiError with validation errors on 422', async () => {
        vi.stubGlobal('fetch', reply(422, { message: 'Invalid.', errors: { email: ['These credentials do not match our records.'] } }));
        const error = await api.post('/login', {}).catch((exc) => exc);
        expect(error).toBeInstanceOf(ApiError);
        expect(error.status).toBe(422);
        expect(error.errors.email[0]).toBe('These credentials do not match our records.');
    });
});
