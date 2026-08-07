"""
prompt_builder.py – constructs all prompts used by the orchestrator.

Context budget strategy
───────────────────────
  Planning phase  : DeepSeek API — generous budget, 15 000 chars of skill docs.
  Coding phase    : Qwen3 at 8192 tokens — skills excluded by default to keep
                    the context lean.  Set INCLUDE_SKILLS_IN_CODE_PROMPT=1 to
                    enable (e.g. when routing to DeepSeek or Claude).

  The coding-phase budget is evaluated at call time, not at import time, so
  .env loading order never causes a stale value.
"""

import os

from skill_loader import Skill, format_skills_for_prompt

# ── Context budgets ────────────────────────────────────────────────────────────
_PLAN_SKILL_CHAR_BUDGET: int = 15_000
_CODE_SKILL_CHAR_BUDGET_WHEN_ENABLED: int = 8_000

# ── Project context (read once at import; stable across the process lifetime) ──
_GITLAB_PROJECT: str = os.environ.get("GITLAB_PROJECT_PATH", "the project")
_DEFAULT_BRANCH: str = os.environ.get("GITLAB_DEFAULT_BRANCH", "main")

# ── Shared rules block ─────────────────────────────────────────────────────────
_RULES = """\
ABSOLUTE RULES – never violate these:
1. You MUST NOT create new database tables.
2. You MUST NOT alter existing tables, columns, indexes, or migrations.
3. You MUST NOT write migration files.
4. You MUST ONLY use the existing database schema as a read reference.
5. You MUST NOT invent or assume table/column names – use only what is provided.\
"""

# ── System prompts ─────────────────────────────────────────────────────────────

PLANNING_SYSTEM_PROMPT = f"""\
You are a senior software architect for the "{_GITLAB_PROJECT}" project.

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

BACKEND REQUIREMENTS (when generating PHP):
- Follow PSR-12 coding standards.
- Write a PHPUnit test for every PHP change.

FRONTEND REQUIREMENTS (when generating Vue.js code):
- Use the Composition API with <script setup>. Do NOT use @vue/compat or the
  Options API unless the project explicitly uses it.
- Always generate a valid package.json with these devDependencies:
    "vitest": "^2.0.0"
    "@vue/test-utils": "^2.0.0"
    "@vitejs/plugin-vue": "^5.0.0"
    "@playwright/test": "1.50.0"   <- exact, no caret: it must match the
                                      browsers in the E2E sandbox image
  and these scripts:
    "test": "vitest run"
    "build": "vite build"
    "preview": "vite preview"
- Generate component tests in __tests__/ directories alongside the .vue files.
  Test file naming: ComponentName.test.js
- Generate Playwright E2E tests in e2e/ at the repository root.
  Test file naming: feature-name.spec.js
- Generate vite.config.js (using @vitejs/plugin-vue) and playwright.config.js
  with webServer.command = "npm run preview" and
  webServer.url = "http://localhost:4173".
- Generate vitest.config.js with environment "jsdom" AND an exclude list that
  keeps Vitest out of the Playwright specs — otherwise Vitest collects
  e2e/*.spec.js and the run dies:
    import {{ configDefaults, defineConfig }} from "vitest/config";
    export default defineConfig({{
      plugins: [vue()],
      test: {{ environment: "jsdom",
               exclude: [...configDefaults.exclude, "e2e/**"] }},
    }});
  Add "jsdom" to devDependencies when you use that environment.

TESTING:
- The test layers that run are detected automatically from the files you
  produce: PHP code is tested with PHPUnit, .vue code with Vitest and then
  Playwright. A task that touches both is tested by all three.
- A frontend-only task needs NO PHPUnit test and NO PHP file. Do not invent
  backend code, a composer.json, or a PHP test just to have something for the
  backend layer — that layer is skipped when the task produces no PHP.
- The reverse also holds: a backend-only task needs no package.json and no
  Vue, Vitest, or Playwright files.

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
    order never results in a stale zero value.
    """
    include = os.environ.get("INCLUDE_SKILLS_IN_CODE_PROMPT", "0").strip()
    return _CODE_SKILL_CHAR_BUDGET_WHEN_ENABLED if include == "1" else 0


# ── Public builder functions ───────────────────────────────────────────────────

def build_plan_prompt(
    issue: dict,
    skills: "list[Skill] | None" = None,
    schema_context: str = "",
) -> tuple[str, str]:
    """
    Return (system_prompt, user_prompt) for the planning phase.

    Parameters
    ----------
    issue:
        Redmine issue dict (must contain 'id', 'subject', 'description').
    skills:
        Skill objects loaded by skill_loader; injected within _PLAN_SKILL_CHAR_BUDGET.
        Planning uses DeepSeek which has a large context, so be generous.
    schema_context:
        Optional read-only database schema description.
    """
    issue_id = issue.get("id", "?")
    subject = (issue.get("subject", "") or "").strip()
    description = (issue.get("description", "") or "").strip()

    schema_section = ""
    if schema_context:
        schema_section = (
            f"\n## Database Schema (READ-ONLY – do not modify)\n"
            f"{schema_context.strip()}\n"
        )

    skills_section = ""
    if skills:
        formatted = format_skills_for_prompt(skills, char_budget=_PLAN_SKILL_CHAR_BUDGET)
        if formatted:
            skills_section = f"\n## Skill Documentation\n{formatted}\n"

    user_prompt = f"""\
## Task
Redmine Issue #{issue_id}: {subject}

### Description
{description or "(no description provided)"}
{schema_section}{skills_section}
## Required Plan Structure
Produce a numbered implementation plan covering:
1. Objective – one-sentence summary of what must be achieved
2. Files to create (path + purpose)
3. Files to modify (path + what changes and why)
4. Implementation steps per file (method names, logic, data flow)
5. Test cases that must pass, grouped by the layers this task touches
   (PHPUnit / Vitest / Playwright) — file name + test names. Omit any layer
   the task does not touch.
6. Risks or ambiguities (if any)

Write the plan now. No code, no preamble.\
"""
    return PLANNING_SYSTEM_PROMPT, user_prompt


def build_code_prompt(
    issue: dict,
    plan: str,
    skills: "list[Skill] | None" = None,
    schema_context: str = "",
) -> tuple[str, str]:
    """
    Return (system_prompt, user_prompt) for the code-generation phase.

    Parameters
    ----------
    issue:
        Redmine issue dict.
    plan:
        The approved implementation plan produced in the planning phase.
    skills:
        Skill objects.  Injected only when INCLUDE_SKILLS_IN_CODE_PROMPT=1
        (resolved at call time) to protect Qwen's 8 192-token context window.
    schema_context:
        Optional read-only database schema description.
    """
    issue_id = issue.get("id", "?")
    subject = (issue.get("subject", "") or "").strip()
    description = (issue.get("description", "") or "").strip()

    schema_section = ""
    if schema_context:
        schema_section = (
            f"\n## Database Schema (READ-ONLY – do not modify)\n"
            f"{schema_context.strip()}\n"
        )

    skills_section = ""
    code_budget = _get_code_skill_budget()
    if skills and code_budget > 0:
        formatted = format_skills_for_prompt(skills, char_budget=code_budget)
        if formatted:
            skills_section = f"\n## Skill Documentation\n{formatted}\n"

    user_prompt = f"""\
## Task
Redmine Issue #{issue_id}: {subject}

### Description
{description or "(no description provided)"}
{schema_section}
## Approved Implementation Plan
{plan.strip()}
{skills_section}
## Instructions
Implement the approved plan above:
- Produce every file listed in the plan using the FILE format.
- Files must be complete and immediately deployable.
- Include the test files for every layer the plan touches (PHPUnit for PHP,
  Vitest + Playwright for Vue.js). Skip the layers the plan does not touch.
- Do NOT touch the database schema.\
"""
    return CODING_SYSTEM_PROMPT, user_prompt
