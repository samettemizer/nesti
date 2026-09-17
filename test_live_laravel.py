"""
test_live_laravel.py – real-container proof of the Laravel + PrimeVue pipeline.

OPT-IN. Unlike test_graph_smoke.py (which fakes every external service), this
script drives the actual sandbox images end to end and therefore needs:

  • a working Docker daemon and ~4 GB of images:
        docker build -t nesti-sandbox-php  -f Dockerfile.sandbox      .
        docker build -t nesti-sandbox-node -f Dockerfile.sandbox.node .
        docker build -t nesti-sandbox-e2e  -f Dockerfile.sandbox.e2e  .
  • outbound network (packagist for composer, npm for the frontend layers)
  • patience: a full pass takes tens of minutes on a slow link.

It is the only automated check of the three sandbox recipes and of
tool_laravel_bootstrap, so it lives in the repo next to the smoke suite.

What it proves, in order:
  1. a greenfield directory becomes a Laravel 13 + Scramble + PrimeVue app
  2. a realistic feature (migration → model → factory → FormRequest →
     controller → API Resource → route → tests → Vue component → specs) is
     written through the FILE-block contract
  3. `php artisan migrate` + `php artisan test` go green in the PHP sandbox
  4. the OpenAPI gate passes for a documented surface AND fails, naming the
     route, for an undocumented one
  5. Vitest and Playwright go green, the latter against `php artisan serve`

Run:  python test_live_laravel.py [--keep]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from docker_runner import DockerRunner            # noqa: E402
from frontend_runner import FrontendRunner        # noqa: E402
from graph.tools import (                          # noqa: E402
    tool_laravel_bootstrap,
    tool_openapi_export,
)

_OUTPUT_TAIL = 2500          # chars of container output shown on failure
_REQUIRED_IMAGES = ("nesti-sandbox-php", "nesti-sandbox-node", "nesti-sandbox-e2e")

# Files the scaffold must produce before any feature code is written.
_SCAFFOLD_EXPECTED = (
    "artisan",
    "composer.json",
    "routes/api.php",
    "routes/web.php",
    "config/scramble.php",
    "vite.config.js",
    "vitest.config.js",
    "playwright.config.js",
    "resources/js/app.js",
    "resources/views/app.blade.php",
    "tests/TestCase.php",
    "tests/Feature/OpenApiDocumentationTest.php",
)

_results: list[tuple[str, bool, str]] = []


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def _record(step: str, ok: bool, detail: str = "") -> None:
    _results.append((step, ok, detail))
    print(f"\n{'PASS' if ok else 'FAIL'}  {step}" + (f"\n      {detail}" if detail else ""))


def _summary() -> int:
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for step, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {step}")
        if not ok and detail:
            print(f"        {detail.splitlines()[0][:160]}")
    failed = [s for s, ok, _ in _results if not ok]
    if failed:
        print(f"\n{len(failed)} step(s) FAILED: {', '.join(failed)}")
        return 1
    print(f"\nAll {len(_results)} step(s) PASSED ✅")
    return 0


class StepFailed(Exception):
    """Raised to abort the run after the failing step has been recorded."""


def _fail(step: str, detail: str) -> None:
    _record(step, False, detail)
    raise StepFailed(step)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture feature — written through the real FILE-block contract
# ─────────────────────────────────────────────────────────────────────────────

def _block(path: str, lang: str, body: str) -> str:
    return f"### FILE: {path}\n```{lang}\n{body}\n```\n\n"


_MIGRATION = """<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('tasks', function (Blueprint $table) {
            $table->id();
            $table->string('title');
            $table->text('description')->nullable();
            $table->boolean('is_done')->default(false);
            $table->date('due_date')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('tasks');
    }
};"""

_MODEL = """<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;
use Illuminate\\Database\\Eloquent\\Model;

class Task extends Model
{
    use HasFactory;

    protected $fillable = [
        'title',
        'description',
        'is_done',
        'due_date',
    ];

    protected $casts = [
        'is_done' => 'boolean',
        'due_date' => 'date',
    ];
}"""

_FACTORY = """<?php

namespace Database\\Factories;

use Illuminate\\Database\\Eloquent\\Factories\\Factory;

class TaskFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'title' => $this->faker->sentence(3),
            'description' => $this->faker->paragraph(),
            'is_done' => $this->faker->boolean(),
            'due_date' => $this->faker->date(),
        ];
    }
}"""

_SEEDER = """<?php

namespace Database\\Seeders;

use App\\Models\\Task;
use Illuminate\\Database\\Seeder;

class TaskSeeder extends Seeder
{
    public function run(): void
    {
        Task::factory()->count(15)->create();
    }
}"""

_REQUEST = """<?php

namespace App\\Http\\Requests;

use Illuminate\\Foundation\\Http\\FormRequest;

class StoreTaskRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, mixed>
     */
    public function rules(): array
    {
        return [
            'title' => ['required', 'string', 'max:255'],
            'description' => ['nullable', 'string'],
            'due_date' => ['nullable', 'date'],
        ];
    }
}"""

_RESOURCE = """<?php

namespace App\\Http\\Resources;

use Illuminate\\Http\\Request;
use Illuminate\\Http\\Resources\\Json\\JsonResource;

class TaskResource extends JsonResource
{
    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'title' => $this->title,
            'description' => $this->description,
            'is_done' => $this->is_done,
            'due_date' => $this->due_date?->toDateString(),
        ];
    }
}"""

_CONTROLLER = """<?php

namespace App\\Http\\Controllers;

use App\\Http\\Requests\\StoreTaskRequest;
use App\\Http\\Resources\\TaskResource;
use App\\Models\\Task;
use Illuminate\\Http\\JsonResponse;
use Illuminate\\Http\\Resources\\Json\\AnonymousResourceCollection;

class TaskController extends Controller
{
    /**
     * List the tasks, ten per page.
     */
    public function index(): AnonymousResourceCollection
    {
        return TaskResource::collection(Task::query()->latest('id')->paginate(10));
    }

    /**
     * Create a task.
     */
    public function store(StoreTaskRequest $request): JsonResponse
    {
        $task = Task::create($request->validated());

        return TaskResource::make($task)->response()->setStatusCode(201);
    }
}"""

# routes/api.php is registered by bootstrap/app.php under the /api prefix, so
# the URIs here must NOT repeat it.
_ROUTES_API = """<?php

use App\\Http\\Controllers\\TaskController;
use Illuminate\\Support\\Facades\\Route;

Route::get('/tasks', [TaskController::class, 'index']);
Route::post('/tasks', [TaskController::class, 'store']);"""

_FEATURE_TEST = """<?php

namespace Tests\\Feature;

use App\\Models\\Task;
use Illuminate\\Foundation\\Testing\\RefreshDatabase;
use Tests\\TestCase;

class TaskApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_index_returns_ten_tasks_per_page(): void
    {
        Task::factory()->count(15)->create();

        $this->getJson('/api/tasks')
            ->assertOk()
            ->assertJsonStructure(['data', 'meta' => ['per_page']])
            ->assertJsonPath('meta.per_page', 10)
            ->assertJsonCount(10, 'data');
    }

    public function test_store_rejects_an_empty_title(): void
    {
        $this->postJson('/api/tasks', ['title' => ''])
            ->assertStatus(422)
            ->assertJsonValidationErrors('title');
    }

    public function test_store_creates_the_task(): void
    {
        $this->postJson('/api/tasks', ['title' => 'Write the migration'])
            ->assertCreated();

        $this->assertDatabaseHas('tasks', ['title' => 'Write the migration']);
    }
}"""

_COMPONENT = """<template>
    <div class="task-table" data-testid="task-table">
        <InputText v-model="search" placeholder="Search tasks" data-testid="task-search" />
        <DataTable :value="filtered">
            <Column field="title" header="Title" sortable />
            <Column field="due_date" header="Due date" sortable />
            <Column field="is_done" header="Done" sortable />
        </DataTable>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import InputText from 'primevue/inputtext';

const props = defineProps({
    tasks: { type: Array, default: () => [] },
});

const emit = defineEmits(['refresh']);

const rows = ref([...props.tasks]);
const search = ref('');

const filtered = computed(() => {
    const needle = search.value.trim().toLowerCase();

    if (!needle) {
        return rows.value;
    }

    return rows.value.filter((task) => String(task.title).toLowerCase().includes(needle));
});

async function load() {
    const response = await fetch('/api/tasks', { headers: { Accept: 'application/json' } });
    const payload = await response.json();

    rows.value = payload.data ?? [];
    emit('refresh');
}

onMounted(() => {
    if (props.tasks.length === 0) {
        load();
    }
});
</script>"""

_COMPONENT_SPEC = """import { mount } from '@vue/test-utils';
import Aura from '@primeuix/themes/aura';
import PrimeVue from 'primevue/config';
import { describe, expect, it } from 'vitest';
import TaskTable from '../TaskTable.vue';

const tasks = [
    { id: 1, title: 'Alpha task', due_date: '2026-01-01', is_done: false },
    { id: 2, title: 'Beta task', due_date: '2026-02-01', is_done: true },
];

function build() {
    return mount(TaskTable, {
        props: { tasks },
        global: { plugins: [[PrimeVue, { theme: { preset: Aura } }]] },
    });
}

describe('TaskTable', () => {
    it('renders the three columns', () => {
        const headers = build().findAll('th').map((th) => th.text());

        expect(headers.join(' ')).toContain('Title');
        expect(headers.join(' ')).toContain('Due date');
        expect(headers.join(' ')).toContain('Done');
    });

    it('renders the rows handed in through the tasks prop', () => {
        const text = build().text();

        expect(text).toContain('Alpha task');
        expect(text).toContain('Beta task');
    });
});"""

_E2E_SPEC = """import { expect, test } from '@playwright/test';

test('the task table renders against the real application', async ({ page }) => {
    await page.goto('/');

    await expect(page.locator('[data-testid="task-table"]')).toBeVisible();
    await expect(page.locator('th', { hasText: 'Title' }).first()).toBeVisible();
    await expect(page.locator('th', { hasText: 'Due date' }).first()).toBeVisible();
    await expect(page.locator('[data-testid="task-search"]')).toBeVisible();
});"""

# The one template the fixture is allowed to extend: registering a feature
# component is exactly what the coding prompt tells the model to do here.
_APP_JS = """import { createApp } from 'vue';
import PrimeVue from 'primevue/config';
import Aura from '@primeuix/themes/aura';
import 'primeicons/primeicons.css';
import TaskTable from './components/TaskTable.vue';

const app = createApp({});

app.use(PrimeVue, { theme: { preset: Aura } });
app.component('task-table', TaskTable);

app.mount('#app');"""

_APP_BLADE = """<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>{{ config('app.name', 'Laravel') }}</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body>
    <div id="app">
        <task-table></task-table>
    </div>
</body>
</html>"""

# A route Scramble is told to skip: the gate must notice it is registered but
# absent from the exported document.
_CONTROLLER_WITH_HIDDEN = _CONTROLLER.replace(
    "use Illuminate\\Http\\Resources\\Json\\AnonymousResourceCollection;",
    "use Dedoc\\Scramble\\Attributes\\ExcludeRouteFromDocs;\n"
    "use Illuminate\\Http\\Resources\\Json\\AnonymousResourceCollection;",
).replace(
    "    /**\n     * Create a task.\n     */",
    "    #[ExcludeRouteFromDocs]\n"
    "    public function hidden(): JsonResponse\n"
    "    {\n"
    "        return response()->json(['hidden' => true]);\n"
    "    }\n\n"
    "    /**\n     * Create a task.\n     */",
)

_ROUTES_API_WITH_HIDDEN = _ROUTES_API + (
    "\nRoute::post('/hidden', [TaskController::class, 'hidden']);"
)


def _feature_blocks() -> str:
    return "".join((
        _block("database/migrations/2026_01_01_000000_create_tasks_table.php", "php", _MIGRATION),
        _block("app/Models/Task.php", "php", _MODEL),
        _block("database/factories/TaskFactory.php", "php", _FACTORY),
        _block("database/seeders/TaskSeeder.php", "php", _SEEDER),
        _block("app/Http/Requests/StoreTaskRequest.php", "php", _REQUEST),
        _block("app/Http/Resources/TaskResource.php", "php", _RESOURCE),
        _block("app/Http/Controllers/TaskController.php", "php", _CONTROLLER),
        _block("routes/api.php", "php", _ROUTES_API),
        _block("tests/Feature/TaskApiTest.php", "php", _FEATURE_TEST),
        _block("resources/js/components/TaskTable.vue", "vue", _COMPONENT),
        _block("resources/js/components/__tests__/TaskTable.test.js", "js", _COMPONENT_SPEC),
        _block("e2e/tasks.spec.js", "js", _E2E_SPEC),
        _block("resources/js/app.js", "js", _APP_JS),
        _block("resources/views/app.blade.php", "blade", _APP_BLADE),
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Steps
# ─────────────────────────────────────────────────────────────────────────────

def step_images() -> None:
    import docker

    try:
        client = docker.from_env()
        missing = []
        for image in _REQUIRED_IMAGES:
            try:
                client.images.get(image)
            except Exception:  # pylint: disable=broad-except
                missing.append(image)
    except Exception as exc:  # pylint: disable=broad-except
        _fail("0. sandbox images", f"Docker unavailable: {type(exc).__name__}: {exc}")
    if missing:
        _fail("0. sandbox images", f"missing: {', '.join(missing)} – build them first")
    _record("0. sandbox images", True, ", ".join(_REQUIRED_IMAGES))


def step_bootstrap(repo: str) -> None:
    subprocess.run(["git", "init", "-q", repo], check=True)

    started = time.monotonic()
    result = tool_laravel_bootstrap(repo)
    took = time.monotonic() - started
    if not result["success"]:
        _fail("1. greenfield bootstrap", result["error"][-_OUTPUT_TAIL:])

    detail = result["result"]
    if not detail["created"] or detail["mode"] != "scaffold":
        _fail(
            "1. greenfield bootstrap",
            f"expected created=True/mode=scaffold, got {detail['created']}/{detail['mode']}",
        )

    missing = [rel for rel in _SCAFFOLD_EXPECTED if not Path(repo, rel).is_file()]
    if missing:
        _fail("1. greenfield bootstrap", f"scaffold did not produce: {', '.join(missing)}")

    package = json.loads(Path(repo, "package.json").read_text(encoding="utf-8"))
    pin = package.get("devDependencies", {}).get("@playwright/test")
    if pin != "1.50.0":
        _fail("1. greenfield bootstrap", f'@playwright/test must be exactly "1.50.0", got {pin!r}')
    for dependency in ("vue", "primevue", "@primeuix/themes", "primeicons"):
        if dependency not in package.get("dependencies", {}):
            _fail("1. greenfield bootstrap", f"package.json is missing {dependency}")
    for dependency in ("vite", "laravel-vite-plugin"):
        if dependency not in package.get("devDependencies", {}):
            _fail("1. greenfield bootstrap",
                  f"the skeleton's {dependency} was dropped by the merge")
    if "/database/*.sqlite*" not in Path(repo, ".gitignore").read_text(encoding="utf-8"):
        _fail("1. greenfield bootstrap", ".gitignore does not ignore the sandbox sqlite file")

    routing = Path(repo, "bootstrap/app.php").read_text(encoding="utf-8")
    if "routes/api.php" not in routing:
        _fail("1. greenfield bootstrap", "bootstrap/app.php does not register routes/api.php")

    _record(
        "1. greenfield bootstrap",
        True,
        f"Laravel + Scramble + PrimeVue scaffolded in {took:.0f}s; "
        f"@playwright/test pinned {pin}; {detail['reason']}",
    )


def step_write_feature(repo: str) -> None:
    written_ok, written = DockerRunner.write_files(_feature_blocks(), repo)
    if not written_ok:
        _fail("2. write the fixture feature", "no FILE blocks were parsed")
    expected = 14
    if len(written) != expected:
        _fail("2. write the fixture feature",
              f"expected {expected} files, wrote {len(written)}: {written}")
    _record("2. write the fixture feature", True, ", ".join(written))


def step_phpunit(repo: str) -> None:
    started = time.monotonic()
    passed, output = DockerRunner().run_tests(repo)
    took = time.monotonic() - started
    if not passed:
        _fail("3. migrate + php artisan test", output[-_OUTPUT_TAIL:])
    if "Tests:" not in output:
        _fail("3. migrate + php artisan test",
              f"output does not look like `php artisan test`:\n{output[-_OUTPUT_TAIL:]}")
    marker = [line for line in output.splitlines() if line.strip().startswith("Tests:")]
    _record("3. migrate + php artisan test", True,
            f"{marker[0].strip() if marker else 'green'} ({took:.0f}s)")


def step_openapi_green(repo: str) -> None:
    started = time.monotonic()
    result = tool_openapi_export(repo)
    took = time.monotonic() - started
    if not result["success"]:
        _fail("4a. OpenAPI gate (documented)", result["error"][-_OUTPUT_TAIL:])

    detail = result["result"]
    if not detail["passed"]:
        _fail("4a. OpenAPI gate (documented)",
              f"undocumented={detail['undocumented']}\n{detail['output'][-_OUTPUT_TAIL:]}")
    if "/api/tasks" not in detail["paths"]:
        _fail("4a. OpenAPI gate (documented)",
              f"/api/tasks absent from the exported paths: {detail['paths']}")
    if not Path(repo, "openapi.json").is_file():
        _fail("4a. OpenAPI gate (documented)", "openapi.json was not written into the repo")

    _record("4a. OpenAPI gate (documented)", True,
            f"paths={detail['paths']} ({took:.0f}s)")


def step_openapi_red(repo: str) -> None:
    Path(repo, "app/Http/Controllers/TaskController.php").write_text(
        _CONTROLLER_WITH_HIDDEN, encoding="utf-8")
    Path(repo, "routes/api.php").write_text(_ROUTES_API_WITH_HIDDEN, encoding="utf-8")
    try:
        result = tool_openapi_export(repo)
        if not result["success"]:
            _fail("4b. OpenAPI gate (undocumented)", result["error"][-_OUTPUT_TAIL:])
        detail = result["result"]
        if detail["passed"]:
            _fail("4b. OpenAPI gate (undocumented)",
                  "the gate passed even though /api/hidden is excluded from the docs")
        if not any("api/hidden" in entry for entry in detail["undocumented"]):
            _fail("4b. OpenAPI gate (undocumented)",
                  f"undocumented list does not name the hidden route: {detail['undocumented']}")
        if "Undocumented API routes" not in detail["output"]:
            _fail("4b. OpenAPI gate (undocumented)",
                  "layer output does not tell the model what to document")
        _record("4b. OpenAPI gate (undocumented)", True,
                f"undocumented={detail['undocumented']}")
    finally:
        # Restore the green surface so the frontend layers run against it.
        Path(repo, "app/Http/Controllers/TaskController.php").write_text(
            _CONTROLLER, encoding="utf-8")
        Path(repo, "routes/api.php").write_text(_ROUTES_API, encoding="utf-8")


def step_vitest(repo: str) -> None:
    started = time.monotonic()
    passed, output = FrontendRunner().run_vitest(repo)
    took = time.monotonic() - started
    if not passed:
        _fail("5. Vitest component layer", output[-_OUTPUT_TAIL:])
    _record("5. Vitest component layer", True, f"green ({took:.0f}s)")


def step_playwright(repo: str) -> None:
    started = time.monotonic()
    passed, output = FrontendRunner().run_playwright(repo)
    took = time.monotonic() - started
    if not passed:
        _fail("6. Playwright E2E layer", output[-_OUTPUT_TAIL:])
    _record("6. Playwright E2E layer", True,
            f"green against `php artisan serve` ({took:.0f}s)")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="keep the temporary workspace for inspection")
    parser.add_argument("--from-step", type=int, default=0,
                        help="(debugging) skip ahead; requires --repo")
    parser.add_argument("--repo", help="(debugging) reuse an existing workspace")
    args = parser.parse_args()

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(levelname)s %(name)s – %(message)s",
    )

    repo = args.repo or tempfile.mkdtemp(prefix="nesti-live-")
    print(f"workspace: {repo}")

    try:
        step_images()
        if args.from_step <= 1:
            step_bootstrap(repo)
        if args.from_step <= 2:
            step_write_feature(repo)
        if args.from_step <= 3:
            step_phpunit(repo)
        if args.from_step <= 4:
            step_openapi_green(repo)
            step_openapi_red(repo)
        if args.from_step <= 5:
            step_vitest(repo)
        if args.from_step <= 6:
            step_playwright(repo)
    except StepFailed:
        pass
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        exit_code = _summary()
        if args.keep or args.repo:
            print(f"\nworkspace kept at {repo}")
        else:
            # The sandboxes run as root, so files they create may not be
            # removable by this process; report rather than crash.
            shutil.rmtree(repo, ignore_errors=True)
            if Path(repo).exists():
                print(f"\nworkspace {repo} could not be fully removed "
                      f"(root-owned container leftovers); remove it with:\n"
                      f"  docker run --rm -v /tmp:/hosttmp alpine "
                      f"rm -rf /hosttmp/{Path(repo).name}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
