# Redmine Issue Writing Guideline

This document explains how to write Redmine issues for Nesti and how the orchestrator interprets them.

---

## Table of Contents

1. [Language Rule](#language-rule)
2. [Issue Structure](#issue-structure)
3. [Issue Lifecycle](#issue-lifecycle)
4. [Skill URLs](#skill-urls)
5. [Context Budgets](#context-budgets)
6. [Frontend Issues (Vue.js)](#frontend-issues-vuejs)
7. [Example Issues](#example-issues)
8. [Common Mistakes](#common-mistakes)
9. [How Retries Work](#how-retries-work)

---

## Language Rule

**All issue subjects and descriptions must be written in English.** The system
will still function otherwise, but output quality drops significantly.

The LLM providers behind the orchestrator produce far more consistent and
higher-quality results with English prompts. Code identifiers, file paths, and
API terminology are already English — keeping the issue in the same language
removes an unnecessary translation layer.

---

## Issue Structure

### Subject

The subject must summarise the task in one sentence. Start with an action verb
(Add, Fix, Implement, Refactor, Remove).

**Good examples:**
- `Add email notification when a new comment is posted`
- `Fix pagination bug on the products listing page`
- `Implement role-based access control for the admin panel`

**Bad examples:**
- `notification` *(too vague)*
- `bug fix` *(which bug?)*
- `improve the site` *(not actionable)*

### Description

The description consists of two required sections, one strongly recommended,
and one optional:

1. **Context** *(required)* – What is the current situation? Why is this
   feature needed?
2. **Requirements** *(required)* – What changes must be made? What behaviour
   is expected? Name concrete files, methods, and endpoints where you can.
3. **Acceptance Criteria** *(strongly recommended)* – Testable assertions
   describing the finished behaviour. Each criterion becomes a test; issues
   without them force the model to invent its own test scope, and retries
   lose precision (see [How Retries Work](#how-retries-work)).
4. **Skill URLs** *(optional)* – URLs of reference documents. They can appear
   anywhere in the description; the system detects them automatically. A
   dedicated heading is not required.

---

## Issue Lifecycle

Knowing what happens after you press "Create" helps you write for it:

1. **Pickup** — The orchestrator polls the project and processes **one issue
   at a time, oldest ID first**, among issues in **New** status.
2. **Lock** — The issue moves to **In Progress**. The issue text is captured
   at pickup; edits made after this point are invisible to the running job.
3. **Success** — A Merge Request is opened from a `feature/issue-{id}-{slug}`
   branch into the default branch, titled `[Issue #id] {subject}`. The MR
   description contains the implementation plan and the final test output.
   The issue is **closed** with a note linking to the MR.
4. **Failure** — After all attempts are exhausted (or after an unexpected
   crash), the issue is **reopened (New)** with a note containing the reason
   and the last test output, truncated to the first 1,000 characters.
   Clarify the issue text; it will be picked up again on a later poll.

One issue produces at most one Merge Request. Unrelated features belong in
separate issues.

---

## Skill URLs

The orchestrator automatically detects any `http://` or `https://` URL in the
issue **subject and description**. The documents at these URLs are fetched and
injected into the **planning phase** as additional context.

The PrimeVue documentation URLs used throughout this guide are examples only —
any publicly reachable text document can serve as a skill.

### When to use them

- Component documentation for the UI library in use
- Project-specific coding convention `.md` files
- API contracts or schema references
- Documents describing security or architectural constraints

### URL format

URLs can appear anywhere in the description text:

```
The new table must use the PrimeVue DataTable component:
https://primevue.org/llms/components/datatable.md

Search input must use PrimeVue InputText:
https://primevue.org/llms/components/inputtext.md
```

**Tip:** Many modern libraries expose LLM-friendly documentation endpoints
under `/llms/` paths or as `llms.txt`. Prefer these over regular HTML pages —
they are cleaner, smaller, and parse better.

### Fetch constraints

- URLs must be publicly reachable — no logins, no VPN-only hosts.
- Only text-based responses are accepted (`text/*`, JSON, XML). Binary
  content such as PDFs, images, or archives is rejected with an
  "unsupported content type" warning.
- URLs are consumed **in order of appearance**. Put the most important
  document first: once the character budget runs out, later URLs are
  truncated or skipped entirely.

### Failed fetches

If a URL is unreachable, returns empty content, or produces an unexpected
error, the system sends a Telegram notification and continues without that
skill document. The orchestrator never halts because of a skill failure.

### Limits

| Parameter | Value |
|-----------|-------|
| Maximum characters per URL | 12,000 |
| Total character budget, planning phase | 15,000 |
| Coding phase, default | 0 — skills excluded |
| Coding phase with `INCLUDE_SKILLS_IN_CODE_PROMPT=1` | 8,000 |

---

## Context Budgets

The orchestrator enforces fixed **character** budgets for skill documentation.
These budgets are hardcoded and apply regardless of which LLM provider ends up
serving the call:

**Planning phase:** up to 15,000 characters of skill documentation are
injected alongside the issue.

**Coding phase:** skills are **excluded by default**. This conservative
default exists to protect small-context local models (e.g. an 8,192-token
Qwen3) on installations that enable them — but it applies even when local
models are disabled, which is the default installation. If your cascade
effectively runs on large-context providers (DeepSeek / Claude), set
`INCLUDE_SKILLS_IN_CODE_PROMPT=1` in `.env` to inject up to 8,000 characters
of skill documentation into the coding prompt as well. The shipped
`.env.example` already sets this flag to `1`.

Regardless of the flag, the coding prompt always contains the system prompt,
the issue description, the approved plan, and — on retries — the previous
attempt together with its failure output.

---

## Frontend Issues (Vue.js)

When your issue produces Vue.js code, the pipeline automatically extends
testing beyond PHPUnit:

```
PHPUnit (backend)  →  Vitest (component tests)  →  Playwright (E2E tests)
```

**Stack detection is automatic.** If the generated code contains `.vue` files,
the frontend test layers run. No declaration is needed in the issue.

### What the system generates for Vue issues

- Component tests in `__tests__/` directories (Vitest + Vue Test Utils)
- E2E tests in the `e2e/` directory (Playwright, headless Chromium)
- A `package.json` with the required dev dependencies and scripts
- `playwright.config.js` configured to serve the built app via `vite preview`

### Writing testable frontend requirements

Frontend acceptance criteria should describe **observable behaviour** — what
the user sees and does — because these become Playwright assertions:

```
Acceptance Criteria:
- The page displays a table with columns: name, size, uploaded_at
- Clicking a column header sorts the rows by that column
- Typing in the search input filters rows without a page reload
- Clicking "Delete" opens a confirmation dialog before removal
```

Component-level criteria (props, events, computed values) become Vitest tests:

```
- The FileTable component accepts a `files` prop (array)
- Emits a "delete" event with the file id when Delete is confirmed
```

---

## Example Issues

### 1. Simple Issue (backend only)

> Single feature, no external documents needed.

**Subject:**
```
Add a "last seen" timestamp to user profiles
```

**Description:**
```
Context:
Currently user profiles do not display any activity information.
Product wants to show when a user was last active on the platform.

Requirements:
- Display the last_seen_at column (already exists in the users table) on
  the user profile page (resources/views/profile/show.blade.php).
- Format: "Last seen: 3 hours ago" using Carbon's diffForHumans().
- If the value is null, show "Never logged in".
- Add a PHPUnit test to assert the formatted string appears in the view.

Acceptance Criteria:
- The profile page shows "Last seen: 3 hours ago" for a user last active
  three hours ago
- The profile page shows "Never logged in" when last_seen_at is null
```

---

### 2. Medium Complexity Issue (frontend, single skill URL)

> Multiple layers affected.

**Subject:**
```
Replace jQuery file table in admin panel with PrimeVue DataTable
```

**Description:**
```
Context:
The admin file listing currently uses a jQuery DataTables plugin which is
difficult to maintain and does not fit the new Vue.js frontend stack.

Requirements:
- Create a new Vue 3 component at resources/js/components/FileTable.vue.
- Use the PrimeVue DataTable component (see skill URL below).
- Fetch data from the existing GET /api/admin/files endpoint.
- Columns: name, size, uploaded_at, actions (download, delete).
- Support client-side sorting and a search/filter input.
- Do NOT modify the API endpoint or its response structure.
- Register the component in resources/js/app.js.

Acceptance Criteria:
- The table renders all four columns with data from the API
- Clicking a column header sorts rows client-side
- The search input filters visible rows as the user types

Skill documentation:
https://primevue.org/llms/components/datatable.md
```

---

### 3. Multi-Skill Issue (frontend, multiple skill URLs)

> Multiple PrimeVue component documents required.

**Subject:**
```
Build a file upload dialog for the media library using PrimeVue
```

**Description:**
```
Context:
The media library currently has no upload interface. Users must use an
external FTP tool. We need an in-browser upload dialog.

Requirements:
- Create a Vue 3 component at resources/js/components/MediaUploadDialog.vue.
- Use PrimeVue Dialog as the wrapper (see skill URL below).
- Use PrimeVue FileUpload inside the dialog for multi-file selection.
- On confirm, POST files to /api/media/upload (multipart/form-data).
- Show upload progress per file using the FileUpload progress feature.
- On success, emit an "uploaded" event with the list of new file URLs.
- Do NOT create new database tables; the existing media table is sufficient.

Acceptance Criteria:
- Clicking "Upload" in the media library opens the dialog
- Multiple files can be selected and queued
- A progress bar is visible per file during upload
- The dialog closes and the file list refreshes on success

Skill documentation:
https://primevue.org/llms/components/fileupload.md
https://primevue.org/llms/components/dialog.md
```

---

### 4. Bug Fix Issue

> Sufficient context is provided to reproduce and fix an existing bug.

**Subject:**
```
Fix incorrect total price calculation in the cart when a discount coupon is applied
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
- Fix the rounding logic in CartService::applyDiscount() to use integer
  arithmetic (work in cents, convert at the end) or PHP's bcmath functions.
- File: app/Services/CartService.php, method: applyDiscount().
- Do NOT change the database schema.
- Add a PHPUnit test that covers the exact scenario above and at least two
  additional edge cases (e.g. coupon value exceeds item price, zero-value cart).
```

---

## Common Mistakes

| Mistake | Why it fails | How to fix |
|---------|-------------|------------|
| Subject too generic (`"bug fix"`, `"feature"`) | The model cannot determine what to do | Use verb + object format |
| Only outcomes stated, no requirements | Unclear which layers must change | Fill in Context + Requirements sections |
| No acceptance criteria | The model invents its own test scope; retry feedback loses precision | Write testable acceptance criteria |
| Skill URL unreachable or behind auth | Fetch fails, Telegram warning fires | Verify the URL is publicly accessible before submitting |
| Skill document too large (>12,000 chars) | Content is truncated at 12,000 chars | Split the document or link only the relevant component page |
| Multiple unrelated features in one issue | Planning and code quality degrade | Open a separate issue per feature |
| Requesting schema changes (`CREATE TABLE`, migrations) | The system categorically refuses | Define features using existing tables only |
| More than 4 skill URLs | Context budget overflows, later URLs get cut | Split the issue or pick the most critical URLs |
| Editing an issue after it moved to In Progress | The run captured the text at pickup; later edits are invisible to it | Wait for the result, then update the reopened issue and let it re-run |
| Frontend criteria written as implementation details | Cannot be converted into Playwright assertions | Describe observable user behaviour instead |

---

## How Retries Work

Understanding the retry loop helps you write better issues:

1. Code is generated and all applicable test layers run
   (PHPUnit → Vitest → Playwright).
2. If any layer fails, the failure output is **appended to the conversation
   history** — the model sees exactly what it produced and why it failed.
3. The provider tier escalates (local → DeepSeek → Claude Sonnet; disabled
   tiers are skipped) and code is regenerated with that failure context.
4. After all retries are exhausted (default: 3 total attempts), the issue is
   reopened with the last failure output attached as a note (truncated to
   the first 1,000 characters).

**Practical implication:** precise acceptance criteria produce precise test
failures, which produce precise retry context. Vague criteria produce vague
failures the model cannot learn from.

---

*The orchestrator assumes a web developer (php) role by default.
Supporting another language or runtime requires revising `prompt_builder.py`
and the sandbox images.*