#!/usr/bin/env python3
"""
scripts/seed_live_issues.py – create the three Phase 5 live-run issues.

The issues drive one full pass of the Laravel + PrimeVue pipeline:

    1. backend + database + /api  → PHPUnit + OpenAPI layers
    2. PrimeVue DataTable         → Vitest + Playwright layers
    3. PrimeVue Dialog form       → all four layers, posting to issue 1's API

Idempotent: an issue whose subject already exists in the configured "new"
status is skipped, so re-running after a partial seed never duplicates work.

RedmineClient deliberately exposes no issue-creation method (the orchestrator
only reads and transitions issues), so this script POSTs directly rather than
widening that client's surface for a one-off operator tool.

Usage:
    python scripts/seed_live_issues.py --dry-run
    python scripts/seed_live_issues.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from dotenv import load_dotenv

load_dotenv()

_REQUEST_TIMEOUT = 30
_LIST_LIMIT = 100

ISSUES: tuple[dict[str, str], ...] = (
    {
        "subject": "Add a paginated /api/tasks endpoint backed by a tasks table",
        "description": """Context: the application has no task storage yet.

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
""",
    },
    {
        "subject": "Show the task list with a PrimeVue DataTable component",
        "description": """Context: the task API exists but nothing renders it.

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
""",
    },
    {
        "subject": "Add a PrimeVue Dialog form that creates a task",
        "description": """Context: tasks can be listed but not created from the UI.

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
""",
    },
)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "X-Redmine-API-Key": os.environ["REDMINE_API_KEY"],
            "Content-Type": "application/json",
        }
    )
    return session


def _existing_new_subjects(session: requests.Session, base: str, project: str,
                           status_id: int) -> dict[str, int]:
    """Map subject → issue id for every issue already sitting in the new status."""
    response = session.get(
        f"{base}/issues.json",
        params={
            "project_id": project,
            "status_id": status_id,
            "limit": _LIST_LIMIT,
            "sort": "id:asc",
        },
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return {i["subject"]: i["id"] for i in response.json().get("issues", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be created without calling Redmine")
    args = parser.parse_args()

    base = os.environ["REDMINE_URL"].rstrip("/")
    project = os.environ["REDMINE_PROJECT_ID"]
    status_id = int(os.environ.get("REDMINE_NEW_STATUS_ID", "1"))

    if args.dry_run:
        print(f"DRY RUN – would create in project {project!r} with status_id={status_id}\n")
        for index, issue in enumerate(ISSUES, start=1):
            print(f"── Issue {index} ─────────────────────────────────────────────")
            print(f"Subject: {issue['subject']}")
            print(issue["description"])
        return 0

    session = _session()
    existing = _existing_new_subjects(session, base, project, status_id)

    created: list[int] = []
    for issue in ISSUES:
        subject = issue["subject"]
        if subject in existing:
            print(f"SKIP #{existing[subject]} {subject}")
            continue
        payload = {
            "issue": {
                "project_id": project,
                "subject": subject,
                "description": issue["description"],
                "status_id": status_id,
            }
        }
        response = session.post(f"{base}/issues.json", json=payload,
                                timeout=_REQUEST_TIMEOUT)
        if response.status_code not in (200, 201):
            print(f"FAIL  {subject} → HTTP {response.status_code}: {response.text[:300]}")
            return 1
        issue_id = response.json()["issue"]["id"]
        created.append(issue_id)
        print(f"CREATED #{issue_id} {subject}")

    print(f"\nCreated {len(created)} issue(s): {created or '(none – all already seeded)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
