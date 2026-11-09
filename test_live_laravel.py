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
  1. a greenfield directory becomes a Laravel 13 API: Sanctum, Scramble,
     spatie/laravel-permission, the API-only welcome page, the spatie seed data
     and a README — no Vue
  2. a realistic backend feature (migration → model → factory → seeder →
     FormRequest → controller → API Resource → route → tests) is written
     through the FILE-block contract
  3. `php artisan migrate` + `php artisan test` go green in the PHP sandbox
  4. the OpenAPI gate passes for a documented surface AND fails, naming the
     route, for an undocumented one
  8. the starter kit (spatie roles) on that app: a Sakai SPA in .frontend/,
     PHPUnit, the documented /api/login|users|roles|permissions, Vitest and
     Playwright all green
  9. the starter kit (no role schema) on a fresh Laravel skeleton whose
     .env.example is pgsql: phpunit.xml moves to <DB_DATABASE>_test, PHPUnit
     runs on the postgres sidecar, OpenAPI/Vitest/Playwright green
  10. the starter kit (custom roles/permissions tables) on another fresh
     skeleton: every layer green, roles overlay included

Run:  python test_live_laravel.py [--keep] [--from-step N --repo DIR]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import docker_runner                              # noqa: E402
from docker_runner import DockerRunner            # noqa: E402
from frontend_runner import FrontendRunner        # noqa: E402
from graph.tools import (                          # noqa: E402
    tool_laravel_bootstrap,
    tool_openapi_export,
    tool_starter_kit,
)

_OUTPUT_TAIL = 2500          # chars of container output shown on failure
_REQUIRED_IMAGES = ("nesti-sandbox-php", "nesti-sandbox-node", "nesti-sandbox-e2e")

# Files the scaffold must produce before any feature code is written.
_SCAFFOLD_EXPECTED = (
    "artisan",
    "composer.json",
    "routes/api.php",
    "config/scramble.php",
    "config/permission.php",
    "tests/TestCase.php",
    "tests/Feature/OpenApiDocumentationTest.php",
    "tests/Feature/DatabaseSeederTest.php",
    "database/seeders/DatabaseSeeder.php",
    "database/seeders/RolePermissionSeeder.php",
    "database/seeders/UserSeeder.php",
    "resources/views/welcome.blade.php",
    "README.md",
)
_WELCOME_TEXT = ("At Nesti, we use Laravel solely to serve an API. "
                 "Please check the README.md for more information.")

_STARTER_PATHS = ("/api/login", "/api/users", "/api/roles", "/api/permissions")
_CUSTOM_ROLES_MIGRATION = """<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('roles', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->timestamps();
        });

        Schema::create('permissions', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('permissions');
        Schema::dropIfExists('roles');
    }
};
"""

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

    if not list(Path(repo, "database/migrations").glob("*_create_permission_tables.php")):
        _fail("1. greenfield bootstrap", "the spatie/laravel-permission migration was not published")
    composer = json.loads(Path(repo, "composer.json").read_text(encoding="utf-8"))
    for dependency in ("laravel/sanctum", "spatie/laravel-permission", "dedoc/scramble"):
        if dependency not in composer.get("require", {}):
            _fail("1. greenfield bootstrap", f"composer.json does not require {dependency}")
    if _WELCOME_TEXT not in Path(repo, "resources/views/welcome.blade.php").read_text(encoding="utf-8"):
        _fail("1. greenfield bootstrap", "welcome.blade.php lacks the API-only sentence")
    package = json.loads(Path(repo, "package.json").read_text(encoding="utf-8"))
    if "vue" in {**package.get("dependencies", {}), **package.get("devDependencies", {})}:
        _fail("1. greenfield bootstrap", "the API-only scaffold added vue to package.json")
    for dependency in ("vite", "laravel-vite-plugin"):
        if dependency not in package.get("devDependencies", {}):
            _fail("1. greenfield bootstrap", f"the skeleton's {dependency} was dropped")
    user = Path(repo, "app/Models/User.php").read_text(encoding="utf-8")
    if not all(trait in user for trait in ("HasApiTokens", "HasRoles")):
        _fail("1. greenfield bootstrap", "User lacks HasApiTokens/HasRoles")
    if "/database/*.sqlite*" not in Path(repo, ".gitignore").read_text(encoding="utf-8"):
        _fail("1. greenfield bootstrap", ".gitignore does not ignore the sandbox sqlite file")

    routing = Path(repo, "bootstrap/app.php").read_text(encoding="utf-8")
    if "routes/api.php" not in routing:
        _fail("1. greenfield bootstrap", "bootstrap/app.php does not register routes/api.php")

    _record(
        "1. greenfield bootstrap",
        True,
        f"Laravel API + Sanctum + Scramble + spatie scaffolded in {took:.0f}s; {detail['reason']}",
    )


def step_write_feature(repo: str) -> None:
    written_ok, written = DockerRunner.write_files(_feature_blocks(), repo)
    if not written_ok:
        _fail("2. write the backend feature", "no FILE blocks were parsed")
    _record("2. write the backend feature", True, ", ".join(written))


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
        # Restore the green surface so the starter-kit steps run against it.
        Path(repo, "app/Http/Controllers/TaskController.php").write_text(
            _CONTROLLER, encoding="utf-8")
        Path(repo, "routes/api.php").write_text(_ROUTES_API, encoding="utf-8")


_BROWSER_RUN = re.compile(r"Running \d+ tests? using")


# ── Steps 8–10: the starter kit ──────────────────────────────────────────────

def _starter_layers(step: str, app: str, variant: str) -> str:
    """Starter kit on the root app *app* (SPA in .frontend/), then every layer green."""
    result = tool_starter_kit(app, ".", ".frontend")
    if not result["success"]:
        _fail(step, result["error"][-_OUTPUT_TAIL:])
    if result["result"]["variant"] != variant:
        _fail(step, f"variant {result['result']['variant']!r}, expected {variant!r}")
    if Path(app, ".frontend/src/views/pages/Roles.vue").is_file() != (variant != "none"):
        _fail(step, f"Roles.vue presence does not match the {variant} variant")
    passed, output = DockerRunner().run_tests(app)
    if not passed:
        _fail(step, f"PHPUnit:\n{output[-_OUTPUT_TAIL:]}")
    tests = next((line.strip() for line in output.splitlines() if line.strip().startswith("Tests:")), "green")
    api = tool_openapi_export(app)
    if not api["success"] or not api["result"]["passed"]:
        _fail(step, f"OpenAPI:\n{(api.get('error') or api['result']['output'])[-_OUTPUT_TAIL:]}")
    expected = _STARTER_PATHS if variant != "none" else _STARTER_PATHS[:2]
    missing = [path for path in expected if path not in api["result"]["paths"]]
    if missing:
        _fail(step, f"undocumented starter paths {missing}; exported {api['result']['paths']}")
    spa = str(Path(app, ".frontend"))
    passed, output = FrontendRunner().run_vitest(spa)
    if not passed:
        _fail(step, f"Vitest:\n{output[-_OUTPUT_TAIL:]}")
    passed, output = FrontendRunner().run_playwright(spa)
    if not passed or not _BROWSER_RUN.search(output):
        _fail(step, f"Playwright:\n{output[-_OUTPUT_TAIL:]}")
    return f"variant {variant}; PHPUnit {tests}; documented {list(expected)}; Vitest + Playwright green"


def step_starter_kit(repo: str) -> None:
    step = "8. starter kit (spatie) on the scaffolded app"
    _record(step, True, _starter_layers(step, repo, "spatie"))


def _skeleton(step: str, workspace: str) -> None:
    """A fresh Laravel skeleton in *workspace*, created in the PHP sandbox."""
    version = os.environ.get("NESTI_LARAVEL_VERSION", "^13.0")
    script = " ".join([
        "set -e;", docker_runner._CAPTURE_OWNER, docker_runner._TRAP_OWNER,
        f'composer create-project --no-interaction --prefer-dist "laravel/laravel:{version}" /tmp/skel;',
        "rm -rf /tmp/skel/.git;",
        "cp -a /tmp/skel/. /app/",
    ])
    runner = DockerRunner()
    # Harness-only use of the private _run: Nesti itself never creates a bare skeleton.
    passed, output = runner._run(workspace, ["bash", "-lc", script], runner.bootstrap_timeout, "skeleton")
    if not passed or not Path(workspace, "artisan").is_file():
        _fail(step, f"Laravel skeleton:\n{output[-_OUTPUT_TAIL:]}")


def _top_up(step: str, app: str) -> None:
    result = tool_laravel_bootstrap(app)
    if not result["success"]:
        _fail(step, f"top-up:\n{result['error'][-_OUTPUT_TAIL:]}")


def step_starter_plain_pgsql(workspace: str, custom_workspace: str) -> None:
    step = "9. starter kit (no roles) on a pgsql skeleton"
    _skeleton(step, workspace)
    shutil.copytree(workspace, custom_workspace, symlinks=True, dirs_exist_ok=True)
    env = Path(workspace, ".env.example")
    text = re.sub(r"^#?[ \t]*DB_CONNECTION=.*$", "DB_CONNECTION=pgsql",
                  env.read_text(encoding="utf-8"), count=1, flags=re.MULTILINE)
    env.write_text(re.sub(r"^#?[ \t]*DB_DATABASE=.*$", "DB_DATABASE=alt", text, count=1, flags=re.MULTILINE),
                   encoding="utf-8")
    _top_up(step, workspace)
    settings = docker_runner._pgsql_settings(workspace)
    if not settings or settings["DB_DATABASE"] != "alt_test":
        _fail(step, f"phpunit.xml was not pointed at alt_test: {settings}")
    _record(step, True, "phpunit.xml → pgsql alt_test; " + _starter_layers(step, workspace, "none"))


def step_starter_custom(workspace: str) -> None:
    step = "10. starter kit (custom roles) on a skeleton"
    Path(workspace, "database/migrations/2026_01_01_000000_create_roles_and_permissions_tables.php").write_text(
        _CUSTOM_ROLES_MIGRATION, encoding="utf-8")
    _top_up(step, workspace)
    _record(step, True, _starter_layers(step, workspace, "custom"))


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
    # Steps 9–10 build their own skeletons; never the --repo workspace.
    skeletons = [tempfile.mkdtemp(prefix="nesti-live-pgsql-"), tempfile.mkdtemp(prefix="nesti-live-custom-")]
    print(f"workspace: {repo}; skeletons: {', '.join(skeletons)}")

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
        if args.from_step <= 8:
            step_starter_kit(repo)
        if args.from_step <= 10:
            step_starter_plain_pgsql(*skeletons)
            step_starter_custom(skeletons[1])
    except StepFailed:
        pass
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        exit_code = _summary()
        kept = [repo] if args.repo else []
        for workspace in [repo, *skeletons]:
            if args.keep or workspace in kept:
                print(f"\nworkspace kept at {workspace}")
                continue
            # The sandboxes run as root, so files they create may not be
            # removable by this process; report rather than crash.
            shutil.rmtree(workspace, ignore_errors=True)
            if Path(workspace).exists():
                print(f"\nworkspace {workspace} could not be fully removed "
                      f"(root-owned container leftovers); remove it with:\n"
                      f"  docker run --rm -v /tmp:/hosttmp alpine "
                      f"rm -rf /hosttmp/{Path(workspace).name}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
