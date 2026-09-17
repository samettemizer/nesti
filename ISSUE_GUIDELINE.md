# GitLab Issue Writing Guideline

This document explains how to write GitLab issues for Nesti and how the
orchestrator interprets them.

---

## Table of Contents

1. [Language Rule](#language-rule)
2. [The Label Workflow](#the-label-workflow)
3. [Issue Structure](#issue-structure)
4. [What to Name in Requirements](#what-to-name-in-requirements)
5. [API Work and the OpenAPI Gate](#api-work-and-the-openapi-gate)
6. [Frontend Work (PrimeVue 5)](#frontend-work-primevue-5)
7. [Acceptance Criteria per Layer](#acceptance-criteria-per-layer)
8. [Skill URLs and the Vendored Corpus](#skill-urls-and-the-vendored-corpus)
9. [Context Budgets](#context-budgets)
10. [New Repo vs. Existing Repo](#new-repo-vs-existing-repo)
11. [Example Issues](#example-issues)
12. [Common Mistakes](#common-mistakes)
13. [How Retries Work](#how-retries-work)

---

## Language Rule

**All issue titles and descriptions must be written in English.** The system
will still function otherwise, but output quality drops significantly.

The LLM providers behind the orchestrator produce far more consistent and
higher-quality results with English prompts. Code identifiers, file paths, and
API terminology are already English — keeping the issue in the same language
removes an unnecessary translation layer.

---

## The Label Workflow

Nesti uses GitLab Issues for task intake. Intake is **opt-in by label** — an
unlabelled issue is treated as human discussion and never touched.

### How it works

1. **Opt in.** Add the label configured by `GITLAB_ISSUE_LABEL` (default:
   `nesti`) to your issue. Without this label Nesti will never see the issue.
2. **Pickup.** The orchestrator polls the project and processes **one issue at
   a time, oldest `iid` first**, among issues that are open, carry the opt-in
   label, and do **not** carry the lock label. The issue text is captured at
   pickup; edits made after this point are invisible to the running job.
3. **Lock.** Nesti adds the scoped label `nesti::in-progress`. This is Nesti's
   lock — do not add or remove it by hand while a run is active. GitLab scoped
   labels (the `::` form) are mutually exclusive within their scope, so the
   lock is always single-valued.
4. **Success.** Nesti removes the lock label, posts a comment containing the
   Merge Request URL, and closes the issue. The MR body starts with the GitLab
   closing keyword `Closes #<iid>`, so the issue and MR are cross-linked
   automatically.
5. **Failure.** After all retries are exhausted (or after an unexpected crash),
   Nesti removes the lock label and posts a failure comment with the last test
   output. The issue returns to the pending pool and will be picked up again on
   the next poll. Fix the issue text (or the acceptance criteria) before it is
   retried.

### Issue numbers

Issue numbers throughout this guide and in Nesti's logs are the project-scoped
`iid` — the number you see in the GitLab UI (e.g. `#7`), not the global `id`.

### Summary table

| State | GitLab condition |
|-------|------------------|
| Pending | Open + has `nesti` label + does NOT have `nesti::in-progress` |
| In progress | Open + has `nesti::in-progress` |
| Done | Closed |

One issue produces at most one Merge Request. Unrelated features belong in
separate issues.

---

## Issue Structure

### Title

The title must summarise the task in one sentence. Start with an action verb
(Add, Fix, Implement, Refactor, Remove).

The title becomes the branch slug (`feature/issue-<iid>-<slug>`) and the MR
title, so keep it concise and descriptive.

**Good examples:**
- `Add a paginated /api/tasks endpoint backed by a tasks table`
- `Fix pagination bug on the products listing page`
- `Show the task list with a PrimeVue DataTable component`

**Bad examples:**
- `notification` *(too vague)*
- `bug fix` *(which bug?)*
- `improve the site` *(not actionable)*

### Description

The description consists of two required sections, one strongly recommended,
and one optional:

1. **Context** *(required)* — What is the current situation? Why is this
   feature needed?
2. **Requirements** *(required)* — What changes must be made? What behaviour
   is expected? Name concrete files, methods, and endpoints where you can.
3. **Acceptance Criteria** *(strongly recommended)* — Testable assertions
   describing the finished behaviour. Each criterion becomes a test; issues
   without them force the model to invent its own test scope, and retries
   lose precision (see [How Retries Work](#how-retries-work)).
4. **Skill URLs** *(optional)* — URLs of reference documents. They can appear
   anywhere in the description; the system detects them automatically. A
   dedicated heading is not required.

---

## What to Name in Requirements

The pipeline is a **Laravel 13 + PrimeVue 5** architect. Name the Laravel
artefacts explicitly so the planner knows what to create or modify:

| Artefact | What to specify |
|----------|----------------|
| Migration | Table name, columns, types, indexes, defaults |
| Model | `$fillable`, `$casts`, relationships |
| Factory | Which model; Faker conventions if specific |
| Seeder | How many rows, any constraints |
| FormRequest | Validation rules (field, rule list) |
| Controller | Action methods, which routes they serve |
| API Resource | Fields exposed in the JSON response |
| Route entry | HTTP verb, URI, controller method |
| Blade view | Path under `resources/views/` |
| Vue component | Path under `resources/js/components/` |

**Database changes are normal work.** Migrations, model factories, and seeders
are expected. Nesti will **never** edit an existing migration — always ask for
a NEW one. Both `up()` and `down()` are required, and only the Schema
builder / Blueprint API may be used (no raw DDL — the test suite runs on
SQLite).

---

## API Work and the OpenAPI Gate

When your issue adds or changes `/api` routes, state which routes are
added/changed and what the OpenAPI document must contain afterwards.

The pipeline exports `openapi.json` via `php artisan scramble:export` and
compares it against `php artisan route:list --json`. **The attempt fails when
any `/api` route is missing from the document.** This means your requirements
should make the API shapes inferable by Scramble:

- **Typed FormRequest rules** for the request body/query parameters.
- **A JsonResource** for the response shape.
- **A one-line PHPDoc summary** above each controller method.

Scramble derives the OpenAPI spec from these three sources. Explicit
annotations are rarely needed.

**Do not** ask for a PHPUnit test that inspects the generated OpenAPI document.
The pipeline owns that check — `tests/Feature/OpenApiDocumentationTest.php`
already covers the wiring.

---

## Frontend Work (PrimeVue 5)

When your issue produces Vue.js code, name the **PrimeVue 5 component names**
instead of describing raw HTML:

| Purpose | PrimeVue 5 component |
|---------|---------------------|
| Tables | `DataTable` + `Column` |
| Text input | `InputText` |
| Dropdowns | `Select` |
| Date fields | `DatePicker` |
| Buttons | `Button` |
| Modals | `Dialog` / `ConfirmDialog` |
| Feedback | `Toast` / `Message` |
| File uploads | `FileUpload` |
| Navigation | `Menubar` / `Breadcrumb` / `Tabs` |
| Checkboxes | `Checkbox` |
| Numbers | `InputNumber` |
| Org charts | `OrganizationChart` |

### Renamed components from PrimeVue 3/4

The vendored skill catalog carries an alias map, so **old names still resolve
to the correct v5 documentation** — but prefer the v5 name in new issues:

| PrimeVue 3/4 name | PrimeVue 5 name | Notes |
|--------------------|-----------------|-------|
| `Dropdown` | `Select` | Both resolve to the Select doc |
| `Calendar` | `DatePicker` | Both resolve to the DatePicker doc |
| `OrgChart` | `OrganizationChart` | Import path: `primevue/organizationchart` |

### Stack detection

Detection is automatic. If the generated code contains `.vue` files, the
frontend test layers run. No declaration is needed in the issue.

| Your issue produces | Layers that run |
|---------------------|-----------------|
| PHP only | PHPUnit → OpenAPI (if API routes touched) |
| Vue only (no PHP) | Vitest → Playwright |
| Both (fullstack) | PHPUnit → OpenAPI → Vitest → Playwright |

**Frontend-only issues are fully supported.** Not every website change has a
backend part. Do **not** add backend requirements to a purely visual or
client-side issue just to give PHPUnit something to run — that only widens the
change and makes failures harder to read.

---

## Acceptance Criteria per Layer

Write acceptance criteria that map to the test layers the issue touches:

| Layer | What to assert | Example |
|-------|---------------|---------|
| **PHPUnit** | Feature/Unit: HTTP status, JSON shape, database state, validation errors | `GET /api/tasks` returns 200 with `data` and `meta.per_page = 10` |
| **OpenAPI** | Routes present in the generated document | Both routes appear in the generated OpenAPI document |
| **Vitest** | Props, emitted events, computed values, rendered text | The component accepts a `tasks` prop and emits `refresh` |
| **Playwright** | Observable user behaviour in the browser | Clicking "New task" opens the dialog |

### Layer-specific rules

- A **backend-only issue** needs no Vue file, no Vitest criteria, and no
  Playwright criteria.
- A **frontend-only issue** needs no PHPUnit criteria and must not be padded
  with invented backend requirements.
- Omit layers the task does not touch — the pipeline skips them automatically.

### Practical warnings

**E2E database state.** The Playwright sandbox database contains exactly what
`DatabaseSeeder` creates (the sandbox runs `php artisan migrate --force
--seed`). Do **not** write E2E criteria that assume rows exist unless you also
ask for a seeder that creates them. If the issue adds a table and a seeder,
name the seeder explicitly in the requirements.

**Component-test DOM.** Component-test criteria should be about rendered text,
props, and events rather than PrimeVue's internal DOM structure. For example,
a `DataTable` with no rows still renders an empty-message row, so expecting
`findAll('tr')` to be empty fails — assert the empty message is shown instead.

---

## Skill URLs and the Vendored Corpus

### Vendored corpus (automatic)

Nesti ships a **vendored, offline skill corpus** containing 92 PrimeVue
component docs, 2 PrimeVue guide pages, and 24 Laravel topic docs (~3.2 MB,
committed). The correct documents are selected **automatically** from the
issue title and description text via alias and trigger matching — you do not
need to paste a URL for any component or topic in the corpus.

For example, mentioning "DataTable" in your issue automatically injects the
PrimeVue DataTable documentation. Mentioning "migration" injects the Laravel
migrations topic. This is deterministic and offline: no network request is
made for vendored content.

### When to paste a URL

Paste a URL only for documentation **outside** the vendored corpus — a
third-party package, an internal spec, or a project-specific convention
document. Any `http://` or `https://` URL found anywhere in the title or
description is fetched and injected.

**Tip:** Many modern libraries expose LLM-friendly documentation endpoints
under `/llms/` paths or as `llms.txt`. Prefer these over regular HTML pages —
they are cleaner, smaller, and parse better.

### Fetch constraints

- URLs must be publicly reachable — no logins, no VPN-only hosts.
- Only text-based responses are accepted (`text/*`, JSON, XML). Binary
  content such as PDFs, images, or archives is rejected with an
  "unsupported content type" warning.
- Each URL is capped at **12,000 characters**; content beyond that is
  truncated.
- Request timeout: 15 seconds per URL.

### Failed fetches

If a URL is unreachable, returns empty content, or produces an unexpected
error, the system sends a Telegram notification and continues without that
skill document. The orchestrator never halts because of a skill failure.

---

## Context Budgets

The orchestrator enforces fixed **character** budgets for skill documentation.
These budgets are hardcoded and apply regardless of which LLM provider ends up
serving the call:

### Vendored corpus (always injected)

| Phase | Budget |
|-------|--------|
| Planning | 20,000 chars |
| Coding | 14,000 chars |

Each vendored document is capped at 7,000 characters before the phase budget
is applied. The vendored corpus is always injected — it requires no
configuration.

### Issue-URL skills

| Phase | Budget |
|-------|--------|
| Planning | 15,000 chars |
| Coding (default) | 0 — skills excluded |
| Coding with `INCLUDE_SKILLS_IN_CODE_PROMPT=1` | 8,000 chars |

The coding-phase default of 0 exists to protect small-context local models
(e.g. an 8,192-token Qwen3) on installations that enable them. If your cascade
effectively runs on large-context providers (DeepSeek / Claude), set
`INCLUDE_SKILLS_IN_CODE_PROMPT=1` in `.env` to inject issue-URL skills into
the coding prompt as well.

Regardless of the flag, the coding prompt always contains the system prompt,
the issue description, the approved plan, and — on retries — the previous
attempt together with its failure output.

---

## New Repo vs. Existing Repo

### Empty repository (greenfield)

An empty GitLab repository is scaffolded into a full **Laravel 13 + Scramble +
PrimeVue** application on the first issue. The first Merge Request contains the
skeleton plus the requested feature. This means the very first issue can ask
for database tables, API endpoints, and Vue components — everything will be
created from scratch.

### Existing Laravel application

An existing Laravel repository is only **topped up** with the files needed for
the testing pipeline (e.g. `vitest.config.js`, `playwright.config.js`,
`tests/Feature/OpenApiDocumentationTest.php`) when they are absent. The
existing application structure, routes, and configuration are preserved.

### Non-Laravel PHP repository

A `composer.json` **without** `artisan` is refused outright. Nesti will not
scaffold over a foreign PHP application — doing so would destroy it. Resolve
the project setup before filing issues.

---

## Example Issues

### 1. Backend + Database + API (PHPUnit + OpenAPI layers)

> New migration, model, factory, seeder, API resource, two routes, Feature
> tests, and OpenAPI coverage.

**Title:**
```
Add a paginated /api/tasks endpoint backed by a tasks table
```

**Description:**
```
Context: the application has no task storage yet.

Requirements:
- New migration creating a `tasks` table: `id`, `title` string, `description`
  text nullable, `is_done` boolean default false, `due_date` date nullable,
  timestamps.
- `Task` model with `$fillable` and `$casts`.
- `TaskFactory`.
- `TaskSeeder` seeding 15 tasks via Faker.
- `GET /api/tasks` paginated 10 per page, returning a `TaskResource` collection.
- `POST /api/tasks` validated by `StoreTaskRequest`: `title` required string
  max 255, `description` nullable string, `due_date` nullable date.
- Feature tests for both routes.

Acceptance Criteria:
- `GET /api/tasks` returns 200 with `data` and `meta.per_page = 10`.
- `POST /api/tasks` with an empty title returns 422.
- The created task appears in the database.
- Both routes appear in the generated OpenAPI document.
```

---

### 2. Frontend Listing (Vitest + Playwright layers)

> PrimeVue DataTable consuming an existing API. No backend changes.

**Title:**
```
Show the task list with a PrimeVue DataTable component
```

**Description:**
```
Context: the task API exists but nothing renders it.

Requirements:
- `resources/js/components/TaskTable.vue` fetching `GET /api/tasks`.
- PrimeVue `DataTable` + `Column` for `title`, `due_date` and `is_done`.
- Sortable columns.
- A search input filtering rows client-side.
- Mounted on `/`.

https://primevue.dev/llms/components/datatable.md

Acceptance Criteria:
- The table renders the three columns.
- Clicking the `title` header sorts the rows.
- Typing in the search box filters rows without a reload.
- The component accepts a `tasks` prop and emits `refresh`.
```

---

### 3. Frontend Form (all four layers)

> PrimeVue Dialog posting to an existing API. Touches both frontend and
> backend (Playwright drives the full app, seeder data matters).

**Title:**
```
Add a PrimeVue Dialog form that creates a task
```

**Description:**
```
Context: tasks can be listed but not created from the UI.

Requirements:
- `resources/js/components/TaskCreateDialog.vue` using PrimeVue `Dialog`,
  `InputText`, `DatePicker` and `Button`.
- Posts to `POST /api/tasks`.
- Shows the 422 validation messages inline with PrimeVue `Message`.
- Emits `created` and refreshes the table.
- A Playwright spec covering the happy path and the empty-title error.

https://primevue.dev/llms/components/dialog.md

Acceptance Criteria:
- Clicking "New task" opens the dialog.
- Submitting an empty title shows the validation message.
- Submitting a valid title closes the dialog and the new row appears in the
  table.
```

---

### 4. Bug Fix (backend only)

> Sufficient context to reproduce and fix an existing bug in a Laravel app.

**Title:**
```
Fix incorrect total price calculation when a discount coupon is applied
```

**Description:**
```
Context:
When a percentage discount coupon is applied to a cart that contains items
with fractional prices, the final total is sometimes off by 1 cent due to
a floating-point rounding issue in CartService::applyDiscount().

Steps to reproduce:
1. Add an item priced at $19.99 to the cart.
2. Apply coupon "SAVE10" (10% discount).
3. Expected total: $17.99.  Actual total: $18.00.

Requirements:
- Fix the rounding logic in app/Services/CartService.php, method:
  applyDiscount() — use integer arithmetic (work in cents, convert at the
  end) or PHP's bcmath functions.
- Do NOT change the database schema.
- Add a PHPUnit Feature test that covers the exact scenario above and at
  least two additional edge cases (e.g. coupon value exceeds item price,
  zero-value cart).

Acceptance Criteria:
- applyDiscount(19.99, 10) returns 17.99.
- applyDiscount(0.00, 10) returns 0.00.
- applyDiscount(5.00, 100) returns 0.00 (100% discount).
```

---

## Common Mistakes

| Mistake | Why it fails | How to fix |
|---------|-------------|------------|
| Title too generic (`"bug fix"`, `"feature"`) | The model cannot determine what to do | Use verb + object format |
| Only outcomes stated, no requirements | Unclear which layers must change | Fill in Context + Requirements sections |
| No acceptance criteria | The model invents its own test scope; retry feedback loses precision | Write testable acceptance criteria |
| Missing the `nesti` label | Nesti will never see the issue | Add the opt-in label before or after creating the issue |
| Editing an issue after `nesti::in-progress` appears | The run captured the text at pickup; later edits are invisible to it | Wait for the result, fix the issue text, and let the next poll retry it |
| Adding/removing `nesti::in-progress` by hand | Breaks the lock protocol | Let Nesti manage the lock label |
| Skill URL unreachable or behind auth | Fetch fails, Telegram warning fires | Verify the URL is publicly accessible before submitting |
| Skill document too large (>12,000 chars) | Content is truncated at 12,000 chars | Link only the relevant component page |
| Multiple unrelated features in one issue | Planning and code quality degrade | Open a separate issue per feature |
| Frontend criteria that assume database rows exist | The E2E sandbox contains only what `DatabaseSeeder` creates | Ask for a seeder or create data through the UI/API in the spec |
| Frontend criteria written as implementation details | Cannot be converted into Playwright assertions | Describe observable user behaviour instead |
| Asking for changes to an existing migration | Nesti refuses to edit existing migrations | Ask for a NEW migration that alters the table |
| Requiring raw DDL (`CREATE TABLE`, `ALTER TABLE`) | The test suite runs on SQLite; vendor-specific SQL breaks it | Describe the schema; the model uses the Blueprint API |
| Filing against a non-Laravel PHP repo | A `composer.json` without `artisan` is refused | Set up Laravel first, then file the issue |

---

## How Retries Work

Understanding the retry loop helps you write better issues:

1. Code is generated, the stack is detected, and the applicable test layers run
   in order: **PHPUnit → OpenAPI → Vitest → Playwright**. Layers that do not
   apply to the issue are skipped, and each layer is a gate — a red layer
   stops the next from starting.
2. If any layer fails, the failure output is **appended to the conversation
   history** — the model sees exactly what it produced and why it failed.
3. The provider tier escalates (local → DeepSeek → Claude Sonnet; disabled
   tiers are skipped) and code is regenerated with that failure context.
4. The retry budget is `MAX_CODE_RETRIES + 1` total attempts (default: 3),
   **shared across all four layers** — not per layer. All layers funnel into
   one escalation step. `attempt` increments once per code-generation run.
5. After all retries are exhausted, the lock label is removed and a failure
   comment is posted. The issue returns to the pending pool and will be
   retried on the next poll.

**Stale files are pruned on retry.** Each retry must re-emit the complete set
of files. A file the previous attempt wrote and the new attempt does not
re-emit is **deleted** from the workspace, so a renamed migration cannot leave
two `create_<table>_table` migrations behind.

**Practical implication:** precise acceptance criteria produce precise test
failures, which produce precise retry context. Vague criteria produce vague
failures the model cannot learn from.

---

*The orchestrator assumes a Laravel 13 + PrimeVue 5 architect role. The
vendored skill corpus, sandbox images, and testing pipeline are coupled to
this stack.*
