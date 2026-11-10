import { flushPromises, mount } from '@vue/test-utils';
import PrimeVue from 'primevue/config';
import { describe, expect, it, vi } from 'vitest';
import Users from '@/views/pages/Users.vue';

vi.mock('@/service/api', () => ({
    api: {
        get: vi.fn().mockResolvedValue({
            data: [
                { id: 1, name: 'Admin', email: 'admin@example.com', created_at: '2026-01-01T00:00:00Z', roles: ['admin'] },
                { id: 2, name: 'Ann', email: 'ann@example.com', created_at: '2026-01-02T00:00:00Z', roles: ['viewer'] }
            ],
            links: {},
            meta: { total: 25 }
        })
    }
}));

describe('Users', () => {
    it('renders the emails and total of a page', async () => {
        const wrapper = mount(Users, { global: { plugins: [PrimeVue] } });
        await flushPromises();
        expect(wrapper.text()).toContain('admin@example.com');
        expect(wrapper.text()).toContain('ann@example.com');
        expect(wrapper.text()).toContain('viewer');
        expect(wrapper.findComponent({ name: 'DataTable' }).props('totalRecords')).toBe(25);
    });
});
