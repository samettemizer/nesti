import { fileURLToPath } from 'node:url';
import { configDefaults, defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  // Absolute Rule 20: never let Vitest collect the Playwright specs.
  test: { environment: 'jsdom', globals: true, exclude: [...configDefaults.exclude, 'e2e/**'] },
});
