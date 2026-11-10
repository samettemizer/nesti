import { api } from '@/service/api';
import router from '@/router';
import { computed, ref } from 'vue';

const user = ref(JSON.parse(localStorage.getItem('auth_user') ?? 'null'));
const token = ref(localStorage.getItem('auth_token'));

// api.js clears storage on a 401; keep the reactive copies in step.
window.addEventListener('auth:expired', () => {
    user.value = null;
    token.value = null;
});

export function useAuth() {
    const isAuthenticated = computed(() => Boolean(token.value));

    async function login(email, password) {
        const data = await api.post('/login', { email, password });
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('auth_user', JSON.stringify(data.user));
        token.value = data.token;
        user.value = data.user;
    }

    async function logout() {
        try {
            await api.post('/logout');
        } catch {
            // The token is discarded locally either way.
        }
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        token.value = null;
        user.value = null;
        await router.push({ name: 'login' });
    }

    return { user, isAuthenticated, login, logout };
}
