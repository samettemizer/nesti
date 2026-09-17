import { fileURLToPath } from 'node:url';
import { configDefaults, defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./resources/js', import.meta.url)),
            // Mirror vite.config.js so specs resolve Vue's runtime compiler.
            vue: 'vue/dist/vue.esm-bundler.js',
        },
    },
    test: {
        environment: 'jsdom',
        globals: true,
        // Absolute Rule 20: Vitest's default include glob otherwise collects
        // the Playwright specs under e2e/ and dies with "Playwright Test did
        // not expect test() to be called here".
        exclude: [...configDefaults.exclude, 'e2e/**'],
    },
});
