<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase
{
    /**
     * Disable Vite asset resolution for the whole suite.
     *
     * The PHP sandbox runs `composer install`, `php artisan migrate` and
     * `php artisan test` — it never runs `npm run build`, so
     * public/build/manifest.json does not exist there. Any Feature test that
     * renders a Blade view containing @vite would otherwise die with
     * "Vite manifest not found", failing the backend layer on infrastructure
     * the model cannot fix by rewriting its code. The frontend layers cover
     * the built assets instead: the E2E sandbox does run `npm run build`.
     */
    protected function setUp(): void
    {
        parent::setUp();

        $this->withoutVite();
    }
}
