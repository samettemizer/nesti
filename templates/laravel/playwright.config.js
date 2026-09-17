import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    // The sandbox runs one container with one browser, and parallel workers
    // against a single `php artisan serve` process are flaky.
    fullyParallel: false,
    workers: 1,
    reporter: 'list',
    use: {
        baseURL: 'http://127.0.0.1:8000',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    webServer: {
        command: 'php artisan serve --host=127.0.0.1 --port=8000',
        url: 'http://127.0.0.1:8000',
        reuseExistingServer: false,
        timeout: 120_000,
    },
});
