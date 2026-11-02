import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '',
                    name: 'dashboard',
                    component: () => import('@/views/Dashboard.vue')
                },
                {
                    path: '/users',
                    name: 'users',
                    component: () => import('@/views/pages/Users.vue')
                }
            ]
        },
        {
            path: '/auth/login',
            name: 'login',
            meta: { public: true },
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/:pathMatch(.*)*',
            name: 'notfound',
            meta: { public: true },
            component: () => import('@/views/pages/NotFound.vue')
        }
    ]
});

router.beforeEach((to) => {
    const token = localStorage.getItem('auth_token');
    if (!token && !to.meta.public) return { name: 'login', query: { redirect: to.fullPath } };
    if (token && to.name === 'login') return { name: 'dashboard' };
});

export default router;
