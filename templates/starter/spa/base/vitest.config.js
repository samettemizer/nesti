import { fileURLToPath, URL } from 'node:url';

import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { configDefaults, defineConfig } from 'vitest/config';

export default defineConfig({
    plugins: [
        vue(),
        Components({
            resolvers: [PrimeVueResolver()]
        })
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    test: {
        environment: 'jsdom',
        setupFiles: ['./vitest.setup.js'],
        // Playwright owns e2e/; Vitest would otherwise collect its specs.
        exclude: [...configDefaults.exclude, 'e2e/**', 'node_modules/**']
    }
});
