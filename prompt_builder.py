"""
prompt_builder.py – constructs all prompts used by the orchestrator.

The orchestrator now drives a Laravel 13 + PrimeVue 5 codebase: backend code is
Laravel, frontend code is Vue 3 with PrimeVue components mounted through Laravel
Vite.

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
"""

import os

from skill_loader import Skill, format_skills_for_prompt

# ── Context budgets ────────────────────────────────────────────────────────────
_PLAN_SKILL_CHAR_BUDGET: int = 15_000              # issue-URL skills, planning phase
_CODE_SKILL_CHAR_BUDGET_WHEN_ENABLED: int = 8_000  # issue-URL skills, coding phase (gated)
_CATALOG_PLAN_BUDGET: int = 20_000                 # vendored corpus, planning phase
_CATALOG_CODE_BUDGET: int = 14_000                 # vendored corpus, coding phase (always on)

# ── Framework versions ─────────────────────────────────────────────────────────
_LARAVEL_MAJOR: str = "13"
_PRIMEVUE_MAJOR: str = "5"

# ── Project context (read once at import; stable across the process lifetime) ──
_GITLAB_PROJECT: str = os.environ.get("GITLAB_PROJECT_PATH", "the project")
_DEFAULT_BRANCH: str = os.environ.get("GITLAB_DEFAULT_BRANCH", "main")

# ── Shared rules block ─────────────────────────────────────────────────────────
# Plain (non-f) string: no interpolation, no braces — nothing to escape.
_RULES = """\
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

# ── System prompts ─────────────────────────────────────────────────────────────

PLANNING_SYSTEM_PROMPT = f"""\
You are a senior Laravel {_LARAVEL_MAJOR} architect and PrimeVue {_PRIMEVUE_MAJOR} frontend architect working on the
"{_GITLAB_PROJECT}" project. The repository IS a Laravel application: backend code is Laravel,
frontend code is Vue 3 with PrimeVue components mounted through Laravel Vite.

Your task in this phase is to produce a detailed IMPLEMENTATION PLAN — no code yet.

{_RULES}

PLANNING STANDARDS:
- Identify every file that needs to be created or modified, with a clear reason.
- List all application layers involved (routes, controllers, services,
  repositories, models, views, tests).
- Flag any ambiguities or risks explicitly.
- Define the test cases the implementation must satisfy, in the layers the
  task actually touches: PHPUnit for PHP, Vitest (component) and Playwright
  (E2E) for Vue.js. A frontend-only task defines no PHPUnit cases; a
  backend-only task defines no Vitest or Playwright cases.
- If skill documentation is supplied in the prompt, incorporate its guidance
  into the plan and reference the source URL where relevant.
- Name the Laravel artefacts explicitly: migration, model, factory, seeder, FormRequest, controller, API Resource, route entry, Blade view, Vue component.
- For API work, state which `/api` routes are added or changed and what the OpenAPI document must contain after the change (Scramble derives it from FormRequest rules, JsonResource shapes, and PHPDoc).
- For UI work, name the **PrimeVue components** to be used (by their PrimeVue {_PRIMEVUE_MAJOR} names) instead of describing raw HTML.
- Test cases grouped by layer: PHPUnit (Feature/Unit) → OpenAPI → Vitest → Playwright; omit layers the task does not touch.

OUTPUT FORMAT:
- Plain markdown, numbered or bulleted lists where appropriate.
- Do NOT write any code in this step.
- Do NOT include pleasantries or meta-commentary.\
"""

CODING_SYSTEM_PROMPT = f"""\
You are a senior developer working on the "{_GITLAB_PROJECT}" project
on the "{_DEFAULT_BRANCH}" branch.

{_RULES}

CODING STANDARDS:
- Match the existing code style of the project.
- Do not create unnecessary files.
- Every change ships with tests in its own layer (see TESTING below).
- If unsure about something, state your assumptions explicitly instead of guessing.

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
  correctly documented. tests/Feature/OpenApiDocumentationTest.php already covers the wiring.

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
  Do not re-register it and do not rewrite resources/js/app.js unless the task adds a global
  service (ToastService, ConfirmationService) — then add only that line.
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
  Keep component specs to behaviour the issue actually names.

TESTING (the layers that run are detected from the files you produce):
- PHPUnit (`php artisan test`) always runs in this Laravel repository, so every PHP change ships
  a Feature or Unit test. Migrations are executed before the suite: a broken migration fails the
  layer.
- The OpenAPI layer runs when the task touches routes/api.php, app/Http/Controllers, or
  app/Http/Resources.
- Vitest and then Playwright run when the task produces .vue files. Playwright drives the real
  application: the sandbox runs `php artisan migrate --force --seed`, `npm run build`, and
  playwright.config.js serves the app with `php artisan serve` on http://127.0.0.1:8000.
- The E2E database therefore contains exactly what database/seeders/DatabaseSeeder.php creates.
  NEVER assume rows exist. If an E2E spec needs data, either register your seeder inside
  DatabaseSeeder::run() (and emit DatabaseSeeder.php as a FILE block) or create the data through
  the UI/API inside the spec itself.
- Use precise Playwright locators: getByRole, getByTestId, or getByText(..., {{ exact: true }}).
  A substring locator such as getByText('Done') matches every cell containing that word and
  fails Playwright's strict mode with "resolved to N elements".
- A backend-only task needs no .vue file, no Vitest spec and no Playwright spec. A frontend-only
  task still keeps the PHP suite green but needs no new PHP code.

OUTPUT FORMAT – use this exact format for every file you produce:

### FILE: <relative/path/to/file.ext>
```<language>
<complete file content>
```

- One FILE block per file. Paths are relative to the repository root.
- Produce every affected file in full – no placeholders like "// rest unchanged".\
"""


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


def _format_catalog_section(catalog_skills: "list[Skill] | None", char_budget: int) -> str:
    """
    Render the vendored Laravel/PrimeVue reference corpus as a prompt section.

    Returns an empty string when no catalog skills are supplied or none fit the
    budget.  The section is headed so it reads before the issue-URL skills.
    """
    if not catalog_skills:
        return ""
    formatted = format_skills_for_prompt(catalog_skills, char_budget=char_budget)
    if not formatted:
        return ""
    return (
        f"\n## Reference Documentation (Laravel {_LARAVEL_MAJOR} / PrimeVue {_PRIMEVUE_MAJOR})\n"
        f"{formatted}\n"
    )


# ── Public builder functions ───────────────────────────────────────────────────

def build_plan_prompt(
    issue: dict,
    skills: "list[Skill] | None" = None,
    catalog_skills: "list[Skill] | None" = None,
    repo_context: str = "",
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
    """
    issue_id = issue.get("id", "?")
    subject = (issue.get("subject", "") or "").strip()
    description = (issue.get("description", "") or "").strip()

    repo_section = ""
    if repo_context:
        repo_section = (
            f"\n## Existing Repository State\n"
            f"{repo_context.strip()}\n"
        )

    catalog_section = _format_catalog_section(catalog_skills, _CATALOG_PLAN_BUDGET)

    skills_section = ""
    if skills:
        formatted = format_skills_for_prompt(skills, char_budget=_PLAN_SKILL_CHAR_BUDGET)
        if formatted:
            skills_section = f"\n## Skill Documentation\n{formatted}\n"

    user_prompt = f"""\
## Task
GitLab Issue #{issue_id}: {subject}

### Description
{description or "(no description provided)"}
{repo_section}{catalog_section}{skills_section}
## Required Plan Structure
Produce a numbered implementation plan covering:
1. Objective – one sentence
2. Database changes – migrations (table/columns/indexes), factories, seeders; "none" if not needed
3. Backend files to create/modify – path + purpose (model, FormRequest, controller, resource, route)
4. API surface – each /api route: method, URI, request shape, response shape; "none" if not needed
5. Frontend files to create/modify – path + which PrimeVue components are used
6. Implementation steps per file (method names, logic, data flow)
7. Test cases per layer that must pass (PHPUnit / OpenAPI / Vitest / Playwright) – file + test names
8. Risks or ambiguities

Write the plan now. No code, no preamble.\
"""
    return PLANNING_SYSTEM_PROMPT, user_prompt


def build_code_prompt(
    issue: dict,
    plan: str,
    skills: "list[Skill] | None" = None,
    catalog_skills: "list[Skill] | None" = None,
    repo_context: str = "",
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
    """
    issue_id = issue.get("id", "?")
    subject = (issue.get("subject", "") or "").strip()
    description = (issue.get("description", "") or "").strip()

    repo_section = ""
    if repo_context:
        repo_section = (
            f"\n## Existing Repository State\n"
            f"{repo_context.strip()}\n"
        )

    catalog_section = _format_catalog_section(catalog_skills, _CATALOG_CODE_BUDGET)

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
{catalog_section}{skills_section}
## Instructions
Implement the approved plan above:
- Produce every file listed in the plan using the FILE format.
- Files must be complete and immediately deployable.
- Include the test files for every layer the plan touches (PHPUnit for PHP,
  Vitest + Playwright for Vue.js). Skip the layers the plan does not touch.
- Include the migration, factory and seeder when the plan lists database changes.
- Add or extend the Feature test that proves the new /api route responds as documented.
- Respect "Existing Repository State" above: it lists what the repository ALREADY has.
  Never write a create-table migration for a table listed there — add a separate
  ALTER-style migration instead. Do not re-emit a file listed there unless the plan
  changes it, and reuse the existing model, controller, resource and route rather than
  creating a second copy under a different path.\
"""
    return CODING_SYSTEM_PROMPT, user_prompt
