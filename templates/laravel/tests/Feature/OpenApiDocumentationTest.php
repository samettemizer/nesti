<?php

namespace Tests\Feature;

use Dedoc\Scramble\Generator;
use Dedoc\Scramble\Scramble;
use Tests\TestCase;

class OpenApiDocumentationTest extends TestCase
{
    /**
     * Prove dedoc/scramble is wired into the application.
     *
     * Generating the document directly rather than hitting /docs/api keeps the
     * check independent of the RestrictedDocsAccess gate.
     *
     * Only the envelope is asserted. Scramble omits the `paths` key entirely
     * when no route matches its api_path, which is the correct state for a
     * freshly scaffolded app and for any frontend-only change — asserting
     * `paths` here would fail the backend layer for a reason the model cannot
     * fix. Completeness of `paths` is the OpenAPI layer's job: the pipeline
     * compares `scramble:export` against `route:list` and fails the attempt
     * when a registered /api route is missing from the document.
     */
    public function test_openapi_document_generates(): void
    {
        $doc = app(Generator::class)(Scramble::getGeneratorConfig('default'));

        $this->assertIsArray($doc);
        $this->assertArrayHasKey('openapi', $doc);
        $this->assertArrayHasKey('info', $doc);
    }
}
