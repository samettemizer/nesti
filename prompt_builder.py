"""
prompt_builder.py – constructs all prompts used by the orchestrator.

The orchestrator now drives a Laravel 13 + PrimeVue 5 codebase: backend code is
Laravel, frontend code is Vue 3 with PrimeVue components mounted through Laravel
Vite.

Task scope
──────────
  Both system prompts and the plan structure are composed for the issue's scope
  (issue_scope.py): ``backend``, ``frontend`` or ``fullstack``.  A frontend
  issue gets no database policy, no Laravel/Scramble rules and no PHPUnit
  instructions; a backend issue gets no PrimeVue rules and no Vitest/Playwright
  instructions; fullstack carries both — what every issue received before
  scopes existed, and still the answer whenever the scope is uncertain.

  Each system prompt carries a TASK SCOPE block right after its role: the side
  of the application the change stays on, and documentation files (README.md,
  CHANGELOG.md, docs/) out of the change unless the issue asks for them
  (issue_scope.documentation_request).  The planner declares the scope of its
  plan on line 1 (``SCOPE: …``); node_plan parses it, and the coding prompt
  follows the plan.

Context budget strategy
───────────────────────
  Planning phase  : DeepSeek API — generous budget, 15 000 chars of issue-URL
                    skill docs plus up to 20 000 chars of the vendored
                    Laravel/PrimeVue reference corpus.
  Coding phase    : Qwen3 at 8192 tokens — issue-URL skills excluded by default
                    to keep the context lean.  Set INCLUDE_SKILLS_IN_CODE_PROMPT=1
                    to enable them (e.g. when routing to DeepSeek or Claude).

  Two skill channels, two rules:
    • Issue-URL skills (`skills`)         — gated by INCLUDE_SKILLS_IN_CODE_PROMPT
                                            in the coding phase.
    • Vendored reference corpus
      (`catalog_skills`)                  — injected into the coding phase ALWAYS,
                                            regardless of that flag.  The coder
                                            needs the Laravel/PrimeVue framework
                                            docs on every attempt, so the env flag
                                            never suppresses them; it governs only
                                            the issue-URL skills.

  The coding-phase issue-URL budget is evaluated at call time — not at import
  time — so .env loading order never causes a stale value.

  Phase 8 memory sections (additive, and empty whenever memory is off):
    • Retrieved Reference Snippets — Qdrant chunks of the vendored corpus,
      minus any passage the keyword catalog already injected verbatim.  The
      test is on content, not on the document URL: the catalog injects only
      the first 7 000 chars of a document, and the passages past that cap are
      exactly what the vector index exists to reach.
    • Past Nesti Experience        — plans of similar merged issues (planning).
    • Earlier Failed Attempts      — older failures of this issue (coding).
  If the local Qwen tier starts truncating, lower _QDRANT_CODE_BUDGET rather
  than _CATALOG_CODE_BUDGET: the catalog is the proven source.
"""

import os

from issue_scope import SCOPES, documentation_request
from skill_loader import Skill, format_skills_for_prompt

# ── Context budgets ────────────────────────────────────────────────────────────
_PLAN_SKILL_CHAR_BUDGET: int = 15_000              # issue-URL skills, planning phase
_CODE_SKILL_CHAR_BUDGET_WHEN_ENABLED: int = 8_000  # issue-URL skills, coding phase (gated)
_CATALOG_PLAN_BUDGET: int = 20_000                 # vendored corpus, planning phase
_CATALOG_CODE_BUDGET: int = 14_000                 # vendored corpus, coding phase (always on)
_QDRANT_PLAN_BUDGET: int = 6_000                   # retrieved doc chunks, planning phase
_QDRANT_CODE_BUDGET: int = 5_000                   # retrieved doc chunks, coding phase
_SOLUTION_PLAN_BUDGET: int = 4_000                 # past solved issues, planning phase
_EPISODE_CODE_BUDGET: int = 3_000                  # recalled failures, coding phase

# A past plan larger than the remaining budget is cut to fit, but only when at
# least this much of it survives; a shorter stub carries no reusable approach.
_MIN_SOLUTION_PLAN_CHARS: int = 500
_PLAN_TRUNCATION_MARKER: str = "\n[… rest of this plan truncated …]"

# ── Framework versions ─────────────────────────────────────────────────────────
_LARAVEL_MAJOR: str = "13"
_PRIMEVUE_MAJOR: str = "5"

# ── Project context (read once at import; stable across the process lifetime) ──
_GITLAB_PROJECT: str = os.environ.get("GITLAB_PROJECT_PATH", "the project")
_DEFAULT_BRANCH: str = os.environ.get("GITLAB_DEFAULT_BRANCH", "main")

# ── Prompt blocks ──────────────────────────────────────────────────────────────
# Every system prompt is composed from these blocks for the issue's scope
# (issue_scope.SCOPES): backend-only blocks never reach a frontend issue and vice
# versa; fullstack carries both.  Plain (non-f) strings need no brace escaping;
# the f-strings double the braces of literal JavaScript objects.

_DATABASE_POLICY = """\
DATABASE POLICY — schema work is allowed, and these rules are absolute:
1. Schema changes go into NEW migrations under database/migrations. Never edit, rename, or
   delete a migration that already exists in the repository.
2. Every migration implements both up() and down(); down() reverses up() exactly.
3. Use the Schema builder / Blueprint API only. No raw DDL (DB::statement with CREATE, ALTER,
   DROP): the test suite runs on SQLite and vendor-specific SQL breaks it.
4. Never call migrate:fresh, migrate:reset, db:wipe, or truncate tables from application code,
   seeders, or tests.
5. Test and demo data comes from model factories (database/factories) and seeders
   (database/seeders) with Faker — never from hand-written INSERT statements.
6. Keep models in sync with the schema: $fillable, $casts, relationships, HasFactory.\
"""

# ── TASK SCOPE ─────────────────────────────────────────────────────────────────
_SCOPE_SUMMARY = {
    "backend": "backend — the issue changes the Laravel backend only.",
    "frontend": "frontend — the issue changes the user interface only.",
    "fullstack": "fullstack — the issue may change both the Laravel backend and the Vue frontend.",
}

# What a narrow scope keeps out of the change.  The plumbing a new screen needs
# (a Blade view, a routes/web.php entry) counts as frontend work.
_SCOPE_BOUNDARY = {
    "backend": """\
- No frontend files: no .vue component, JavaScript, CSS, page view, package.json change,
  Vitest spec or Playwright spec. Those layers do not run for a backend change, so nothing
  would verify such a file.""",
    "frontend": """\
- No backend files: no migration, model, factory, seeder, controller, FormRequest, API
  Resource, service, routes/api.php entry or PHPUnit test. The backend the UI needs is listed
  under Existing Repository State; use it as it is. Page plumbing is frontend work: a Blade
  view or a routes/web.php entry that serves the page is allowed.""",
    "fullstack": "",
}

 # Models document their work by habit: without this rule nearly every new
# endpoint also rewrote README.md, which no issue had asked for.
_DOCUMENTATION_OUT_OF_SCOPE = """\
- Documentation is out of scope: the issue does not ask for it. Do not create, modify or
  delete README.md, CHANGELOG.md or any file under docs/ — not to describe what you add,
  and not when a plan, a reference document or a past solution lists them."""

_SCRAMBLE_DOCUMENTS_THE_API = """\
- The /api contract is documented by Scramble from the code itself (FormRequest rules,
  JsonResource shapes, PHPDoc): that is the only API documentation to write."""

# ── Roles ──────────────────────────────────────────────────────────────────────
_PLANNING_ROLE = {
    "backend": f"""\
You are a senior Laravel {_LARAVEL_MAJOR} architect working on the "{_GITLAB_PROJECT}" project.
The repository IS a Laravel application; this issue concerns its backend.""",
    "frontend": f"""\
You are a senior PrimeVue {_PRIMEVUE_MAJOR} frontend architect working on the "{_GITLAB_PROJECT}" project.
The repository IS a Laravel application whose frontend is Vue 3 with PrimeVue components
mounted through Laravel Vite; this issue concerns that frontend.""",
    "fullstack": f"""\
You are a senior Laravel {_LARAVEL_MAJOR} architect and PrimeVue {_PRIMEVUE_MAJOR} frontend architect working on the
"{_GITLAB_PROJECT}" project. The repository IS a Laravel application: backend code is Laravel,
frontend code is Vue 3 with PrimeVue components mounted through Laravel Vite.""",
}

_CODING_ROLE = {
    "backend": f"""\
You are a senior Laravel {_LARAVEL_MAJOR} backend developer working on the "{_GITLAB_PROJECT}" project
on the "{_DEFAULT_BRANCH}" branch.""",
    "frontend": f"""\
You are a senior Vue 3 + PrimeVue {_PRIMEVUE_MAJOR} frontend developer working on the "{_GITLAB_PROJECT}"
project on the "{_DEFAULT_BRANCH}" branch. The repository is a Laravel application; its
frontend is mounted through Laravel Vite.""",
    "fullstack": f"""\
You are a senior Laravel {_LARAVEL_MAJOR} + PrimeVue {_PRIMEVUE_MAJOR} developer working on the "{_GITLAB_PROJECT}" project
on the "{_DEFAULT_BRANCH}" branch.""",
}

# ── Planning ───────────────────────────────────────────────────────────────────
_PLAN_COMMON_STANDARDS = """\
- Identify only the files that need to be created, modified or deleted, each with a clear reason.
- Flag any ambiguities or risks explicitly.
- If skill documentation is supplied in the prompt, incorporate its guidance into the plan and
  reference the source URL where relevant."""

_PLAN_BACKEND_STANDARDS = """\
- Name the Laravel artefacts explicitly: migration, model, factory, seeder, FormRequest,
  controller, API Resource, route entry.
- For API work, state which `/api` routes are added or changed and what the OpenAPI document
  must contain after the change (Scramble derives it from FormRequest rules, JsonResource
  shapes, and PHPDoc)."""

_SEEDER_REMOVAL_STANDARDS = """\
SEEDER REMOVAL — only when the issue explicitly asks to remove an existing seeder:
- Physically delete its PHP file using a DELETE directive, not a FILE block with empty,
  no-op or replacement class content. Do not recreate it for PHPUnit or delete it at test time.
- Remove the seeder's call/registration and unused import from DatabaseSeeder and other
  callers, preserving unrelated seeding. Keep existing models, factories, API and migrations
  unless the issue also requests changes to them.
- Replace tests that invoke the removed seeder with PHPUnit removal coverage:
  assertFileDoesNotExist for its conventional PHP path and assertFalse(class_exists(...))
  using its fully qualified class name as a string, without importing or instantiating it.
- Run DatabaseSeeder through $this->seed(DatabaseSeeder::class) on the isolated migrated
  test database. Assert the affected table gets no rows from the removed seeder, while
  preserving unrelated seed behavior. A retained registration must fail this test.
- Test surviving API/factory behavior using the actual model/resource fields in the
  repository; never invent an alternative boolean or response field.
- A deletion still runs the normal PHPUnit gate; do not skip, weaken or mock it."""

_PLAN_FRONTEND_STANDARDS = f"""\
- For UI work, name the **PrimeVue components** to be used (by their PrimeVue {_PRIMEVUE_MAJOR} names)
  instead of describing raw HTML, and the Vue component files under resources/js/components/.
- Name the existing routes and response shapes the UI relies on, as listed under Existing
  Repository State.
- Name how the feature reaches the served page: the entry chain (routes/web.php → Blade view →
  resources/js/app.js) and the exact change to it — e.g. app.component('TaskTable', TaskTable)
  before app.mount('#app') plus <task-table></task-table> inside <div id="app">, or rendering
  from an existing App.vue root. Keep the PrimeVue/Aura setup and every existing registration.
  An App.vue no entry imports, or a component only a test mounts, is not on the page."""

# The E2E data contract the planner and the coder share (frontend_runner +
# scripts/e2e_fixtures.php consume e2e/nesti-fixtures.json).
_PLAN_E2E_DATA = """\
- E2E data comes from DatabaseSeeder, from records a spec creates through existing UI/API
  routes, or from a fixture declared in e2e/nesti-fixtures.json: the sandbox runs its seeder
  only while the declared GET /api collection is still empty. Plan a fixture only when a
  Playwright case needs real rows from an existing unauthenticated GET /api collection — never
  for a valid empty state, a mocked API or a spec that creates its own data. Name the model's
  existing seeder; when none exists, name Database\\Seeders\\<Model>Seeder without planning that
  class: Nesti verifies it is absent and opens a backend dependency issue."""

_PLAN_TEST_STANDARDS = {
    "backend": """\
- Define the PHPUnit test cases (Feature/Unit) the implementation must satisfy, and the /api
  routes the OpenAPI gate must find documented. A backend task defines no Vitest or
  Playwright cases.""",
    "frontend": """\
- Define the Vitest (component) and Playwright (E2E) test cases the implementation must
  satisfy. At least one Playwright case loads the served page and asserts the feature on real
  data. A frontend task defines no PHPUnit cases.
""" + _PLAN_E2E_DATA,
    "fullstack": """\
- Define the test cases the implementation must satisfy, in the layers the task actually
  touches, grouped by layer: PHPUnit (Feature/Unit) → OpenAPI → Vitest → Playwright. A
  frontend-only task defines no PHPUnit cases; a backend-only task defines no Vitest or
  Playwright cases. A UI change gets at least one Playwright case that loads the served page
  and asserts the feature on real data.
""" + _PLAN_E2E_DATA + """
  A model or /api collection this change adds ships its own factory and seeder.""",
}

_PLANNING_OUTPUT_FORMAT = """\
OUTPUT FORMAT:
- Line 1, alone: the scope of this plan — SCOPE: backend, SCOPE: frontend or SCOPE: fullstack.
- Then plain markdown, numbered or bulleted lists where appropriate.
- Do NOT write any code in this step.
- Do NOT include pleasantries or meta-commentary."""

# The user-prompt plan structure: a backend plan has no frontend section to fill
# with "none", and a frontend plan no database or API-surface section.
_PLAN_STRUCTURE = {
    "backend": (
        "Objective – one sentence",
        'Database changes – migrations (table/columns/indexes), factories, seeders; "none" if not needed',
        "Backend files to create/modify/delete – path + purpose (model, FormRequest, controller, resource, route)",
        'API surface – each /api route: method, URI, request shape, response shape; "none" if not needed',
        "Implementation steps per file (method names, logic, data flow)",
        "Test cases that must pass (PHPUnit; OpenAPI when /api routes change) – file + test names",
        "Risks or ambiguities",
    ),
    "frontend": (
        "Objective – one sentence",
        "Frontend files to create/modify/delete – path + which PrimeVue components are used",
        'Backend used as it is – the existing routes and response shapes the UI calls; "none" if not needed',
        "Implementation steps per file (props, events, state, data flow)",
        "Test cases that must pass (Vitest / Playwright) – file + test names, and where the E2E data comes from",
        "Risks or ambiguities",
    ),
    "fullstack": (
        "Objective – one sentence",
        'Database changes – migrations (table/columns/indexes), factories, seeders; "none" if not needed',
        "Backend files to create/modify/delete – path + purpose (model, FormRequest, controller, resource, route)",
        'API surface – each /api route: method, URI, request shape, response shape; "none" if not needed',
        "Frontend files to create/modify/delete – path + which PrimeVue components are used",
        "Implementation steps per file (method names, logic, data flow)",
        "Test cases per layer that must pass (PHPUnit / OpenAPI / Vitest / Playwright) – file + test names",
        "Risks or ambiguities",
    ),
}

_SCOPE_DECLARATION = {
    "backend": (
        "SCOPE: backend — or SCOPE: fullstack when the issue cannot be solved without frontend "
        "changes (say why under Risks)"
    ),
    "frontend": (
        "SCOPE: frontend — or SCOPE: fullstack when the issue cannot be solved without backend "
        "changes, e.g. the endpoint the UI calls does not exist yet (say why under Risks)"
    ),
    "fullstack": (
        "SCOPE: fullstack — or SCOPE: backend / SCOPE: frontend when the plan changes only that side"
    ),
}

# ── Coding ─────────────────────────────────────────────────────────────────────
_CODING_STANDARDS = """\
CODING STANDARDS:
- Match the existing code style of the project.
- Do not create unnecessary files.
- Every change ships with tests in its own layer (see TESTING below).
- If unsure about something, state your assumptions explicitly instead of guessing."""

_BACKEND_STANDARDS = """\
LARAVEL BACKEND (PHP):
- PSR-12. Controllers in app/Http/Controllers stay thin; business logic goes to app/Services
  or model methods.
- Validation lives in FormRequest classes (app/Http/Requests) with a rules() method, or in an
  explicit $request->validate([...]) call — Scramble can only document those two forms.
- Eloquent models in app/Models with $fillable, $casts, relationships and HasFactory.
- API responses go through API Resources (app/Http/Resources) extending JsonResource.
- API routes go in routes/api.php and are served under the /api prefix. Web routes in
  routes/web.php.
- Feature tests in tests/Feature use the RefreshDatabase trait; unit tests in tests/Unit.
- Do not create or modify: composer.json beyond adding a package you actually need,
  phpunit.xml, bootstrap/app.php, config/scramble.php.

API DOCUMENTATION (Scramble, dedoc/scramble is already installed):
- Every route under /api must end up in the generated OpenAPI document. The pipeline runs
  `php artisan scramble:export --path=openapi.json`, compares the result with
  `php artisan route:list --json`, and FAILS the attempt when an /api route is missing.
- Make it inferable instead of annotating: typed FormRequest rules for the request, a
  JsonResource for the response, and a one-line PHPDoc summary above each controller method.
- Use #[Response(status, description, type: '...')] from Dedoc\\Scramble\\Attributes only when
  the response cannot be inferred. Never use #[ExcludeRouteFromDocs].
- Never add a Gate named viewApiDocs and never change config/scramble.php.
- Do NOT write a PHPUnit test that inspects the generated OpenAPI document. Verifying it is
  the pipeline's own job, and the document's path keys are relative to the server URL, so an
  assertion like assertArrayHasKey('/api/tasks', $doc['paths']) fails even when the route is
  correctly documented. tests/Feature/OpenApiDocumentationTest.php already covers the wiring."""

_FRONTEND_STANDARDS = f"""\
PRIMEVUE FRONTEND (Vue 3):
- Vue 3 Composition API with <script setup>. Never @vue/compat, never the Options API.
- Use PrimeVue {_PRIMEVUE_MAJOR} components instead of hand-written markup: tables → DataTable + Column,
  forms → InputText / Select / DatePicker / Checkbox / InputNumber, actions → Button,
  modals → Dialog / ConfirmDialog, feedback → Toast / Message, uploads → FileUpload,
  navigation → Menubar / Breadcrumb / Tabs.
- Import components per file: import DataTable from 'primevue/datatable'; the import path is
  the lowercase component name (OrganizationChart → 'primevue/organizationchart').
- The PrimeVue plugin and the Aura preset are already registered in resources/js/app.js
  (app.use(PrimeVue, {{ theme: {{ preset: Aura }} }}) with Aura from '@primeuix/themes/aura').
  Never re-register or reconfigure them, and keep every existing import, app.use(...) and
  app.component(...) line. A global service (ToastService, ConfirmationService) adds only its line.
- A feature must reach the page the app serves (routes/web.php → its Blade view → the @vite
  entry resources/js/app.js or app.ts). Make the import/registration/mount change it needs and
  keep the existing root architecture:
  - In-DOM template (createApp({{}}) mounted on <div id="app"> of resources/views/app.blade.php):
    import the component, add app.component('TaskTable', TaskTable) before app.mount('#app'),
    and put <task-table></task-table> inside <div id="app"> of the served Blade view. In-DOM
    tags, props and events are kebab-case (:page-size, @row-select); never self-close a custom tag.
  - SFC root (createApp(App) with an imported App.vue): keep it and render the feature from that
    root. Never convert one architecture into the other.
  - An App.vue that no entry file imports is not a page implementation: nothing renders it.
- Edit the entry file or the Blade view only from its complete body quoted under Existing
  Repository State, emitting the whole file with your change. If that body is named as omitted,
  never reconstruct it from a fragment or replace the boot code by guess; state the assumption.
- An explicit element choice in the issue takes precedence over the PrimeVue preference;
  for example, a requested native input type="date" must stay a native date input.
- Components live in resources/js/components/<Name>.vue; Vitest specs in
  resources/js/components/__tests__/<Name>.test.js; Playwright specs in e2e/<feature>.spec.js.
- vite.config.js, vitest.config.js, playwright.config.js and package.json already exist. You
  may ADD an npm dependency to package.json when the task truly needs one; never remove an
  existing dependency, never change the pinned "@playwright/test": "1.50.0", and never rewrite
  the three config files.
- Tailwind CSS 4 is available for layout utilities.
- In Vitest, assert on rendered text, props and emitted events — never on PrimeVue's
  internal DOM shape. A DataTable with zero rows still renders an empty-message row, so
  expecting findAll('tr') to be empty fails; assert the empty message is shown instead.
  Keep component specs to behaviour the issue actually names."""

_TEST_PHPUNIT = """\
- PHPUnit (`php artisan test`) runs whenever the change creates, modifies or deletes PHP, so
  every PHP change ships a Feature or Unit test. Migrations are executed before the suite:
  a broken migration fails the layer.
- The OpenAPI layer runs when the change touches routes/api.php, app/Http/Controllers,
  app/Http/Resources, or app/Http/Requests."""

_TEST_FRONTEND_LAYERS = """\
- Vitest and then Playwright run when the change touches the frontend (.vue, JavaScript, CSS,
  Blade views, package.json, e2e/). Playwright drives the real application: the sandbox runs
  the migrations and DatabaseSeeder, then the fixtures declared in e2e/nesti-fixtures.json,
  `npm run build`, and playwright.config.js serves the app with `php artisan serve` on
  http://127.0.0.1:8000.
- Test the integration on the served page: at least one Playwright spec opens it (page.goto('/')
  or the feature's web route) and asserts the feature with real API data. A directly mounted
  component or a mocked API proves nothing about integration.
- The E2E database holds what DatabaseSeeder creates plus any declared fixture. NEVER assume
  other rows exist."""

_E2E_FIXTURE_RULE = """\
  If an E2E spec needs data, create it through the UI or the existing /api routes inside the
  spec, or use what DatabaseSeeder creates. Declare a fixture in e2e/nesti-fixtures.json only
  when the spec needs nonempty real rows from an existing unauthenticated GET /api collection —
  never for a valid empty state, a mocked API, or a spec that creates its own data:
  {"version":1,"fixtures":[{"endpoint":"/api/tasks","model":"App\\\\Models\\\\Task","seeder":"Database\\\\Seeders\\\\TaskSeeder"}]}
  The sandbox runs that seeder only while the endpoint is still empty. Name the model's
  existing seeder; when none exists, name Database\\Seeders\\<Model>Seeder anyway and do NOT
  write that class or register it in DatabaseSeeder: Nesti verifies it is absent and opens a
  backend dependency issue. The manifest is test setup, not default seeding — register a seeder
  in DatabaseSeeder::run() only when the issue asks for default seed data. On a retry, re-emit a
  still-needed manifest in full, or emit {"version":1,"fixtures":[]} once it is no longer needed."""

_TEST_E2E_DATA = {
    "frontend": _E2E_FIXTURE_RULE,
    "fullstack": _E2E_FIXTURE_RULE + """
  A model or /api collection this change adds ships its own factory and seeder.""",
}

_TEST_LOCATORS = """\
- Use precise Playwright locators: getByRole, getByTestId, or getByText(..., { exact: true }).
  A substring locator such as getByText('Done') matches every cell containing that word and
  fails Playwright's strict mode with "resolved to N elements"."""

_TEST_SCOPE_NOTE = {
    "backend": """\
- Vitest and Playwright do not run for a backend change: write no .vue file, no Vitest spec
  and no Playwright spec.""",
    "frontend": """\
- Write no PHPUnit test and no PHP class. PHPUnit runs the existing PHP suite only when the
  change touches a PHP file (a Blade view, routes/web.php).""",
    "fullstack": """\
- A backend-only task needs no .vue file, no Vitest spec and no Playwright spec. A frontend-only
  task needs no PHP code and no PHPUnit test.""",
}

_CODE_OUTPUT_FORMAT = """\
OUTPUT FORMAT – use these exact forms for every affected file:

To create or modify a file:
### FILE: <relative/path/to/file.ext>
```<language>
<complete file content>
```

To physically remove a file, emit one standalone line with no code fence or body:
### DELETE: <relative/path/to/file.ext>

- One FILE block or DELETE directive per path; never both. Paths stay inside the repository.
- FILE bodies must be complete — no placeholders like "// rest unchanged".
- DELETE removes the file before tests; an empty FILE body does not delete it.
- Delete only files whose removal the issue/plan requires. Never delete migrations,
  directories, symlinks or .git metadata.
- On every retry re-emit the complete set of FILE blocks AND DELETE directives, including
  files already absent from a previous attempt. An omitted deletion is restored from HEAD."""

_CODE_TEST_INSTRUCTIONS = {
    "backend": """\
- Include a PHPUnit Feature or Unit test for every behaviour the plan changes.
- Include a new migration, factory or seeder only when the plan requires creating it;
  a removal uses DELETE and its removal tests, never a replacement seeder.
- Add or extend the Feature test that proves each new or changed /api route responds as
  documented.""",
    "frontend": """\
- Include a Vitest spec for every component you create or change, and a Playwright spec for
  the user flow the issue names.""",
    "fullstack": """\
- Include the test files for every layer the plan touches (PHPUnit for PHP,
  Vitest + Playwright for Vue.js). Skip the layers the plan does not touch.
- Include a new migration, factory or seeder only when the plan requires creating it;
  a removal uses DELETE and its removal tests, never a replacement seeder.
- Add or extend the Feature test that proves each new or changed /api route responds as
  documented.""",
}

_CODE_REPOSITORY_RULE = {
    "backend": """\
- Respect "Existing Repository State" above: it lists what the repository ALREADY has.
  Never write a create-table migration for a table listed there — add a separate
  ALTER-style migration instead. Do not re-emit a file listed there unless the plan
  changes it, and reuse the existing model, controller, resource and route rather than
  creating a second copy under a different path.""",
    "frontend": """\
- Respect "Existing Repository State" above: it lists what the repository ALREADY has.
  Do not re-emit a file listed there unless the plan changes it, and reuse the existing
  components and routes rather than creating a second copy under a different path.""",
}
_CODE_REPOSITORY_RULE["fullstack"] = _CODE_REPOSITORY_RULE["backend"]


# ── System prompt composition ──────────────────────────────────────────────────

def _normalise_scope(scope: str) -> str:
    """An unknown scope gets the fullstack prompt: narrowing must be earned."""
    return scope if scope in SCOPES else "fullstack"


def _task_scope_block(scope: str, documentation: str) -> str:
    """The TASK SCOPE block both system prompts carry right after their role."""
    lines = [
        f"TASK SCOPE: {_SCOPE_SUMMARY[scope]}",
        "- Change only what the issue needs; every extra file widens the review and the test run.",
    ]
    if _SCOPE_BOUNDARY[scope]:
        lines.append(_SCOPE_BOUNDARY[scope])
    if documentation:
        lines.append(
            f'- The issue asks for documentation ("{documentation}"): change only the documentation '
            "it names,\n  only as far as it asks."
        )
    else:
        lines.append(_DOCUMENTATION_OUT_OF_SCOPE)
    if scope != "frontend":
        lines.append(_SCRAMBLE_DOCUMENTS_THE_API)
    return "\n".join(lines)


def _planning_system_prompt(scope: str, documentation: str) -> str:
    """The planning system prompt for *scope* (already normalised)."""
    standards = [_PLAN_COMMON_STANDARDS]
    if scope != "frontend":
        standards += [_PLAN_BACKEND_STANDARDS, _SEEDER_REMOVAL_STANDARDS]
    if scope != "backend":
        standards.append(_PLAN_FRONTEND_STANDARDS)
    standards.append(_PLAN_TEST_STANDARDS[scope])

    sections = [
        _PLANNING_ROLE[scope],
        "Your task in this phase is to produce a detailed IMPLEMENTATION PLAN — no code yet.",
        _task_scope_block(scope, documentation),
    ]
    if scope != "frontend":
        sections.append(_DATABASE_POLICY)
    sections.append("PLANNING STANDARDS:\n" + "\n".join(standards))
    sections.append(_PLANNING_OUTPUT_FORMAT)
    return "\n\n".join(sections)


def _coding_system_prompt(scope: str, documentation: str) -> str:
    """The coding system prompt for *scope* (already normalised)."""
    testing = ["TESTING (layers follow the files you create, modify or delete):"]
    if scope != "frontend":
        testing.append(_TEST_PHPUNIT)
    if scope != "backend":
        testing += [_TEST_FRONTEND_LAYERS, _TEST_E2E_DATA[scope], _TEST_LOCATORS]
    testing.append(_TEST_SCOPE_NOTE[scope])

    sections = [_CODING_ROLE[scope], _task_scope_block(scope, documentation)]
    if scope != "frontend":
        sections.append(_DATABASE_POLICY)
    sections.append(_CODING_STANDARDS)
    if scope != "frontend":
        sections += [_BACKEND_STANDARDS, _SEEDER_REMOVAL_STANDARDS]
    if scope != "backend":
        sections.append(_FRONTEND_STANDARDS)
    sections.append("\n".join(testing))
    sections.append(_CODE_OUTPUT_FORMAT)
    return "\n\n".join(sections)


# ── Budget helper ──────────────────────────────────────────────────────────────

def _get_code_skill_budget() -> int:
    """
    Return the skill character budget for the coding phase.

    Evaluated at call time — not at import time — so that python-dotenv loading
    order never results in a stale zero value.  Governs only the issue-URL
    skills; the vendored reference corpus is injected unconditionally.
    """
    include = os.environ.get("INCLUDE_SKILLS_IN_CODE_PROMPT", "0").strip()
    return _CODE_SKILL_CHAR_BUDGET_WHEN_ENABLED if include == "1" else 0


def _format_catalog_section(
    catalog_skills: "list[Skill] | None", char_budget: int, scope: str = "fullstack"
) -> str:
    """
    Render the vendored Laravel/PrimeVue reference corpus as a prompt section.

    Returns an empty string when no catalog skills are supplied or none fit the
    budget.  The section is headed so it reads before the issue-URL skills, and
    names only the framework(s) the scope's documents come from.
    """
    if not catalog_skills:
        return ""
    formatted = format_skills_for_prompt(catalog_skills, char_budget=char_budget)
    if not formatted:
        return ""
    frameworks = {
        "backend": f"Laravel {_LARAVEL_MAJOR}",
        "frontend": f"PrimeVue {_PRIMEVUE_MAJOR}",
    }.get(scope, f"Laravel {_LARAVEL_MAJOR} / PrimeVue {_PRIMEVUE_MAJOR}")
    return f"\n## Reference Documentation ({frameworks})\n{formatted}\n"


def chunk_body(chunk: dict) -> str:
    """A retrieved chunk's passage, without the context line the indexer prepends."""
    text = chunk.get("text", "") or ""
    prefix = f"# {chunk.get('doc_title', '')}\n## {chunk.get('heading', '')}\n\n"
    return (text[len(prefix):] if text.startswith(prefix) else text).strip()


def drop_injected_chunks(chunks: "list[dict] | None", injected_text: str) -> list[dict]:
    """
    Keep only the chunks whose passage is NOT already verbatim in *injected_text*.

    *injected_text* is the keyword-catalog documentation of the same prompt.
    De-duplicating on content rather than on the document URL is deliberate:
    the catalog injects a document only up to its 7 000-char cap (and the
    prompt budget may cut it further), so a URL match would also discard the
    passages past the cap — the content the vector index exists to reach.
    """
    if not chunks:
        return []
    if not injected_text:
        return list(chunks)
    return [chunk for chunk in chunks if chunk_body(chunk) not in injected_text]


def _format_retrieved_section(
    chunks: "list[dict] | None",
    char_budget: int,
    exclude_text: str = "",
) -> str:
    """
    Render Qdrant document chunks as a prompt section, best score first.

    A chunk whose passage already appears verbatim in ``exclude_text`` — the
    rendered catalog section of the same prompt — is dropped before any budget
    is spent.  A chunk that does not fit the remaining budget is skipped, never
    truncated.  Returns ``""`` when nothing fits.
    """
    if not chunks:
        return ""
    blocks: list[str] = []
    used = 0
    for chunk in sorted(
        drop_injected_chunks(chunks, exclude_text),
        key=lambda c: c.get("score", 0.0),
        reverse=True,
    ):
        url = chunk.get("doc_url", "")
        title = chunk.get("doc_title", "")
        heading = chunk.get("heading", "")
        body = chunk_body(chunk)
        if not body:
            continue
        block = f"### {title} — {heading}\nSource: {url}\n{body}\n"
        if used + len(block) > char_budget:
            continue
        blocks.append(block)
        used += len(block)
    if not blocks:
        return ""
    return (
        "\n## Retrieved Reference Snippets (semantic search over the vendored corpus)\n"
        + "\n".join(blocks)
    )


def _format_solutions_section(solutions: "list[dict] | None", char_budget: int) -> str:
    """
    Render similar, already-merged issues and the plans that solved them.

    A plan longer than the remaining budget is cut on a line boundary when at
    least ``_MIN_SOLUTION_PLAN_CHARS`` of it survive, otherwise skipped: the
    head of a plan (objective, schema, files) is the reusable part.
    """
    if not solutions:
        return ""
    blocks: list[str] = []
    used = 0
    for solution in solutions:
        header = (
            f"### Issue #{solution.get('issue_id', '?')}: {solution.get('subject', '')}  "
            f"(similarity {solution.get('similarity', 0)}, MR {solution.get('mr_url', '')})\n"
        )
        plan = (solution.get("plan") or "").strip()
        if not plan:
            continue
        room = char_budget - used - len(header) - 1
        if len(plan) > room:
            room -= len(_PLAN_TRUNCATION_MARKER)
            if room < _MIN_SOLUTION_PLAN_CHARS:
                continue
            cut = plan.rfind("\n", 0, room)
            plan = plan[:cut if cut > 0 else room].rstrip() + _PLAN_TRUNCATION_MARKER
        block = f"{header}{plan}\n"
        blocks.append(block)
        used += len(block)
    if not blocks:
        return ""
    return (
        "\n## Past Nesti Experience (similar issues already merged)\n"
        "These are for reference only — the task below is authoritative. Reuse the\n"
        "approach where it fits; do not copy file paths or names that this issue does\n"
        "not ask for.\n"
        + "\n".join(blocks)
    )


def _format_episodes_section(episodes: "list[dict] | None", char_budget: int) -> str:
    """
    Render older failed attempts of this issue (episodic memory).

    An episode that does not fit the remaining budget is skipped, not cut.
    """
    if not episodes:
        return ""
    blocks: list[str] = []
    used = 0
    for episode in episodes:
        summary = (episode.get("summary") or "").strip()
        if not summary:
            continue
        block = (
            f"### Attempt {episode.get('attempt', '?')} — {episode.get('layer', '')} "
            f"(similarity {episode.get('similarity', 0)})\n{summary}\n"
        )
        if used + len(block) > char_budget:
            continue
        blocks.append(block)
        used += len(block)
    if not blocks:
        return ""
    return "\n## Earlier Failed Attempts on This Issue\n" + "\n".join(blocks)


# ── Public builder functions ───────────────────────────────────────────────────

def build_plan_prompt(
    issue: dict,
    skills: "list[Skill] | None" = None,
    catalog_skills: "list[Skill] | None" = None,
    repo_context: str = "",
    retrieved_chunks: "list[dict] | None" = None,
    past_solutions: "list[dict] | None" = None,
    scope: str = "fullstack",
    scope_evidence: str = "",
) -> tuple[str, str]:
    """
    Return (system_prompt, user_prompt) for the planning phase.

    Parameters
    ----------
    issue:
        GitLab issue dict (must contain 'id', 'subject', 'description').
    skills:
        Issue-URL Skill objects loaded by skill_loader; injected within
        _PLAN_SKILL_CHAR_BUDGET.  Planning uses DeepSeek which has a large
        context, so be generous.
    catalog_skills:
        Vendored Laravel/PrimeVue reference Skill objects; injected within
        _CATALOG_PLAN_BUDGET before the issue-URL skills.
    repo_context:
        Inventory of what the cloned repository already contains (migrations,
        models, controllers, resources, requests, route files, Vue
        components).  Without it the model cannot tell a greenfield repo from
        one that already has the feature's foundations, and re-creates them —
        a second `create_<table>_table` migration then fails the PHP layer
        with "table already exists" on every attempt.
    retrieved_chunks:
        Qdrant chunks of the vendored corpus (Phase 8); injected within
        _QDRANT_PLAN_BUDGET, minus passages the catalog section already holds.
    past_solutions:
        Similar merged issues from the Redis solution cache (Phase 8);
        injected within _SOLUTION_PLAN_BUDGET above the reference docs,
        because they are about this project and the docs are generic.
    scope:
        "backend" | "frontend" | "fullstack" from issue_scope.classify_issue;
        composes the system prompt and the plan structure.  Anything else is
        treated as "fullstack".
    scope_evidence:
        Why the issue text got that scope (ScopeDecision.evidence()); shown to
        the planner, which confirms or corrects the scope on line 1 of its plan.
    """
    issue_id = issue.get("id", "?")
    subject = (issue.get("subject", "") or "").strip()
    description = (issue.get("description", "") or "").strip()
    scope = _normalise_scope(scope)

    repo_section = ""
    if repo_context:
        repo_section = (
            f"\n## Existing Repository State\n"
            f"{repo_context.strip()}\n"
        )

    catalog_section = _format_catalog_section(catalog_skills, _CATALOG_PLAN_BUDGET, scope)
    solutions_section = _format_solutions_section(past_solutions, _SOLUTION_PLAN_BUDGET)
    retrieved_section = _format_retrieved_section(
        retrieved_chunks, _QDRANT_PLAN_BUDGET, exclude_text=catalog_section
    )

    skills_section = ""
    if skills:
        formatted = format_skills_for_prompt(skills, char_budget=_PLAN_SKILL_CHAR_BUDGET)
        if formatted:
            skills_section = f"\n## Skill Documentation\n{formatted}\n"

    structure = "\n".join(
        f"{number}. {item}" for number, item in enumerate(_PLAN_STRUCTURE[scope], start=1)
    )
    scope_note = f"Task scope: {scope}" + (f" ({scope_evidence})" if scope_evidence else "") + "."

    user_prompt = f"""\
## Task
GitLab Issue #{issue_id}: {subject}

### Description
{description or "(no description provided)"}
{repo_section}{solutions_section}{catalog_section}{retrieved_section}{skills_section}
## Required Plan Structure
{scope_note}
Line 1 of the plan, alone: {_SCOPE_DECLARATION[scope]}.
Then a numbered implementation plan covering:
{structure}

Write the plan now. No code, no preamble.\
"""
    system_prompt = _planning_system_prompt(scope, documentation_request(subject, description))
    return system_prompt, user_prompt


def build_code_prompt(
    issue: dict,
    plan: str,
    skills: "list[Skill] | None" = None,
    catalog_skills: "list[Skill] | None" = None,
    repo_context: str = "",
    retrieved_chunks: "list[dict] | None" = None,
    recalled_failures: "list[dict] | None" = None,
    scope: str = "fullstack",
) -> tuple[str, str]:
    """
    Return (system_prompt, user_prompt) for the code-generation phase.

    Parameters
    ----------
    issue:
        GitLab issue dict.
    plan:
        The approved implementation plan produced in the planning phase.
    skills:
        Issue-URL Skill objects.  Injected only when INCLUDE_SKILLS_IN_CODE_PROMPT=1
        (resolved at call time) to protect Qwen's 8 192-token context window.
    catalog_skills:
        Vendored Laravel/PrimeVue reference Skill objects.  Injected within
        _CATALOG_CODE_BUDGET on EVERY coding attempt, regardless of
        INCLUDE_SKILLS_IN_CODE_PROMPT — the coder always needs the framework docs.
    repo_context:
        Inventory of what the cloned repository already contains.  See
        build_plan_prompt; the coding phase needs it most, because it is the
        phase that would otherwise emit a duplicate migration.
    retrieved_chunks:
        Qdrant chunks of the vendored corpus (Phase 8); injected within
        _QDRANT_CODE_BUDGET, minus passages the catalog section already holds.
    recalled_failures:
        Older failed attempts of this issue from episodic memory (Phase 8);
        injected within _EPISODE_CODE_BUDGET, last before the instructions,
        where the model is told to correct itself.
    scope:
        The scope of the approved plan (node_plan) — widened by
        node_on_layer_failure when a layer outside it went red.  Composes the
        system prompt and the instructions; anything else means "fullstack".
    """
    issue_id = issue.get("id", "?")
    subject = (issue.get("subject", "") or "").strip()
    description = (issue.get("description", "") or "").strip()
    scope = _normalise_scope(scope)

    repo_section = ""
    if repo_context:
        repo_section = (
            f"\n## Existing Repository State\n"
            f"{repo_context.strip()}\n"
        )

    catalog_section = _format_catalog_section(catalog_skills, _CATALOG_CODE_BUDGET, scope)
    retrieved_section = _format_retrieved_section(
        retrieved_chunks, _QDRANT_CODE_BUDGET, exclude_text=catalog_section
    )
    episodes_section = _format_episodes_section(recalled_failures, _EPISODE_CODE_BUDGET)

    skills_section = ""
    code_budget = _get_code_skill_budget()
    if skills and code_budget > 0:
        formatted = format_skills_for_prompt(skills, char_budget=code_budget)
        if formatted:
            skills_section = f"\n## Skill Documentation\n{formatted}\n"

    user_prompt = f"""\
## Task
GitLab Issue #{issue_id}: {subject}

### Description
{description or "(no description provided)"}
{repo_section}
## Approved Implementation Plan
{plan.strip()}
{catalog_section}{retrieved_section}{episodes_section}{skills_section}
## Instructions
Implement the approved plan above:
- Produce every code and test file the plan lists using FILE blocks, and every physical
  removal using DELETE directives. A file outside TASK SCOPE stays out even when the plan lists it.
- Files must be complete and immediately deployable.
{_CODE_TEST_INSTRUCTIONS[scope]}
{_CODE_REPOSITORY_RULE[scope]}\
"""
    system_prompt = _coding_system_prompt(scope, documentation_request(subject, description))
    return system_prompt, user_prompt
