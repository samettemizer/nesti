import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
    plugins: [
        laravel({
            input: ['resources/css/app.css', 'resources/js/app.js'],
            refresh: true,
        }),
        tailwindcss(),
        vue(),
    ],
    resolve: {
        alias: {
            // Runtime compiler required: app.js relies on Vue compiling the
            // in-DOM template of <div id="app">, so alias to the full build.
            vue: 'vue/dist/vue.esm-bundler.js',
        },
    },
});
