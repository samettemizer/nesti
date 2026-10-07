"""
issue_dependencies.py – fixture dependencies between a paused parent issue and
the backend child issue that adds its missing seeder.

When the E2E sandbox proves that a declared fixture's seeder genuinely does not
exist (e2e_fixtures.py), the parent is not failed and not retried: it is
paused, ONE backend issue asking for that seeder is opened, and the parent
becomes claimable again only after a merge request that closes that child has
actually been merged into the target branch.

Where the truth lives
─────────────────────
GitLab, never Redis: conversation history expires, a worker restarts, and a
dependency must survive both.  The parent carries a durable record — a note
written and read back by GitLabIssuesClient, authored by the automation user,
first line ``NESTI_FIXTURE_DEPENDENCIES_V1`` — and every child carries an
ownership marker in its description.  Both are keyed by
``e2e_fixtures.dependency_key``, so a reconstructed manager with no memory of
the previous run reuses the same child instead of opening a second one.

Ordering is what makes a crash at any point recoverable:

    record intent (creating) → pause parent → find child by marker
    → mark creation submitted → ONE POST → link child (waiting)
    → last merged MR + release_pending → resume → released

A POST whose outcome is unknown is never repeated automatically: the parent
stays paused until the child is found by its marker or an operator resets the
item (see README, "Fixture dependencies").

Transport lives in GitLabIssuesClient; this class only decides.  It makes no
LLM call.
"""

import logging
import posixpath
from datetime import datetime
from pathlib import Path

import git

from e2e_fixtures import (
    CHILD_MARKER,
    MODEL_PREFIX,
    SEEDER_PREFIX,
    active_dependency,
    dependency_key,
    format_child_marker,
    parse_child_marker,
    validate_requirement,
)
from gitlab_issues_client import GitLabIssuesClient
from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)

# A file the attempt itself wrote under one of these makes the missing seeder
# part of the parent's own unmerged backend change, not a dependency.  Blade,
# JavaScript and routes/web.php are page plumbing a frontend change may touch.
_BACKEND_PREFIXES = ("app/", "database/", "bootstrap/", "config/")
_BACKEND_FILES = frozenset({"routes/api.php", "composer.json", "composer.lock", "artisan"})
_API_ROUTES = "routes/api.php"

_TITLE_MAX_CHARS = 255
UNKNOWN_CREATION = "Child creation outcome unknown"
MERGED_UNSATISFIED = "Merged dependency did not satisfy the fixture requirement"
AMBIGUOUS_CHILD = "Ambiguous child ownership markers"


def _normalise_path(raw: str) -> str:
    path = posixpath.normpath(raw.replace("\\", "/").strip())
    return path.removeprefix("./")


def _short_name(fqcn: str) -> str:
    return fqcn.rsplit("\\", 1)[-1]


def _class_path(fqcn: str, prefix: str, directory: str) -> str:
    """Conventional PSR-4 source path of an App\\Models / Database\\Seeders class."""
    return f"{directory}/{fqcn[len(prefix):].replace(chr(92), '/')}.php"


def _closes_line(description: str | None, child_iid: int) -> bool:
    """Nesti's MRs open with exactly ``Closes #<iid>`` (gitlab_client.open_merge_request)."""
    first = (description or "").replace("\r\n", "\n").split("\n", 1)[0]
    return first == f"Closes #{child_iid}"


def _merged_at(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def _commit_sha(detail: dict) -> str | None:
    """Record the merge result when GitLab reports one; fast-forward merges have none."""
    for field in ("merge_commit_sha", "squash_commit_sha", "sha"):
        value = detail.get(field)
        if isinstance(value, str) and len(value) in (40, 64) and all(
            ch in "0123456789abcdef" for ch in value
        ):
            return value
    return None


class FixtureDependencies:
    """Pause a parent on a missing seeder, open its backend child once, resume after merge."""

    def __init__(self, client: GitLabIssuesClient, target_branch: str) -> None:
        self.client = client
        self.target_branch = target_branch

    # ------------------------------------------------------------------
    # Pause
    # ------------------------------------------------------------------

    def pause_for_fixture(
        self, issue_id: int, repo_path: str, requirement: dict, written_files: list[str]
    ) -> dict:
        """
        Turn a verified missing-seeder report into a durable dependency.

        Returns ``{"status": "paused", "child_iid": int | None, "reason": str}``,
        ``{"status": "ineligible", "reason": str}`` when the prerequisite belongs
        to the parent's own unmerged backend change, or ``{"status": "error",
        "reason": str}`` when the parent is no longer open and opted in.  Raises
        on a transport failure; nothing is created before the intent record and
        the pause are both verified.
        """
        requirement = validate_requirement(requirement, with_table=True)
        base_sha, problem = self._eligibility(repo_path, requirement, written_files)
        if problem:
            logger.info("Fixture dependency for issue #%s is ineligible: %s", issue_id, problem)
            return {"status": "ineligible", "reason": problem}

        parent = self.client.get_issue(issue_id)
        if not self._open_and_opted_in(parent):
            return {"status": "error", "reason": "Parent is no longer open and opted in."}
        project_id = parent.get("project_id")
        if not isinstance(project_id, int):
            raise RuntimeError(f"GitLab reported no numeric project id for issue #{issue_id}.")

        key = dependency_key(project_id, issue_id, self.target_branch, requirement)
        state = self.client.get_fixture_state(issue_id) or {
            "version": 1, "project_id": project_id, "release_pending": False, "items": [],
        }
        if state["project_id"] != project_id:
            raise RuntimeError(
                f"Issue #{issue_id}'s dependency record names project {state['project_id']}, "
                f"but the issue belongs to project {project_id}."
            )

        item = next((entry for entry in state["items"] if entry["key"] == key), None)
        if item is None:
            item = {
                "key": key, "state": "creating", "requirement": requirement,
                "base_sha": base_sha, "target_branch": self.target_branch,
                "child_iid": None, "creation_submitted": False,
                "mr_iid": None, "merge_sha": None, "reason": "",
            }
            state["items"].append(item)
            state["release_pending"] = False
        elif item["state"] == "merged":
            # The dependency merged and the same requirement is still unmet:
            # a second child would loop forever, so hold for a human instead.
            item["state"] = "blocked"
            item["reason"] = MERGED_UNSATISFIED
            state["release_pending"] = False
            self.client.save_fixture_state(issue_id, state)
            self._pause(issue_id, requirement)
            telegram_notify(
                f"⛔ Issue <b>#{issue_id}</b> stays paused: dependency #{item['child_iid']} "
                f"(!{item['mr_iid']}) merged, yet GET <code>{requirement['endpoint']}</code> "
                f"still lacks <code>{requirement['seeder']}</code>. Needs a human."
            )
            logger.error("Issue #%s: %s (child #%s).", issue_id, MERGED_UNSATISFIED, item["child_iid"])
            return {"status": "paused", "child_iid": item["child_iid"], "reason": MERGED_UNSATISFIED}

        # Durable intent first, then the verified pause; no child before both.
        self.client.save_fixture_state(issue_id, state)
        self._pause(issue_id, requirement)
        if item["state"] == "creating":
            self._advance_creating(issue_id, state, item)
        return {
            "status": "paused",
            "child_iid": item["child_iid"],
            "reason": self._describe(item),
        }

    def _pause(self, issue_id: int, requirement: dict) -> None:
        note = (
            f"Nesti paused this issue: its E2E fixture needs real rows from "
            f"`GET {requirement['endpoint']}`, and `{requirement['seeder']}` does not exist. "
            "It resumes automatically once the backend dependency is merged."
        )
        if not self.client.pause_issue(issue_id, note=note):
            raise RuntimeError(f"Issue #{issue_id} could not be paused (read-back did not confirm it).")

    def _eligibility(
        self, repo_path: str, requirement: dict, written_files: list[str]
    ) -> tuple[str | None, str | None]:
        """
        ``(base_sha, None)`` when the prerequisite belongs to the target branch;
        ``(None, reason)`` when it belongs to the parent's own unmerged change.
        """
        repo = git.Repo(repo_path)
        try:
            head = repo.head.commit
        except ValueError as exc:
            raise RuntimeError(f"Workspace {repo_path} has no HEAD commit: {exc}") from exc

        authored = sorted({
            path for path in (_normalise_path(raw) for raw in written_files or [])
            if path.startswith(_BACKEND_PREFIXES) or path in _BACKEND_FILES
        })
        if authored:
            return None, (
                f"No dependency issue was opened: the missing {requirement['seeder']} belongs to "
                f"this change's own backend work ({', '.join(authored)}). Provide that data within "
                "this change — ship the model's factory and seeder with the backend files — or let "
                "the spec create its data through the UI or API."
            )

        model_path = _class_path(requirement["model"], MODEL_PREFIX, "app/Models")
        for path in (model_path, _API_ROUTES):
            try:
                committed = (head.tree / path).data_stream.read()
            except KeyError:
                return None, (
                    f"No dependency issue was opened: {path} is not committed on the target "
                    f"branch, so {requirement['seeder']} belongs to this change's backend work."
                )
            working = Path(repo_path, path)
            if not working.is_file() or working.read_bytes() != committed:
                return None, (
                    f"No dependency issue was opened: {path} differs from the target branch, so "
                    f"{requirement['seeder']} belongs to this change's unmerged backend work."
                )
        return head.hexsha, None

    # ------------------------------------------------------------------
    # Child discovery and creation
    # ------------------------------------------------------------------

    def _advance_creating(self, parent_iid: int, state: dict, item: dict) -> None:
        """creating → waiting by linking the one owned child, or by ONE creation POST."""
        matches, corrupt = self._owned_children(parent_iid, state["project_id"], item)
        if corrupt or len(matches) > 1:
            item["state"] = "blocked"
            item["reason"] = AMBIGUOUS_CHILD
            self.client.save_fixture_state(parent_iid, state)
            found = sorted({child["iid"] for child in matches} | set(corrupt))
            telegram_notify(
                f"⛔ Issue <b>#{parent_iid}</b> stays paused: ambiguous dependency children "
                f"{', '.join(f'#{iid}' for iid in found)}. Needs a human."
            )
            logger.error("Issue #%s: %s %s.", parent_iid, AMBIGUOUS_CHILD, found)
            return
        if matches:
            self._link(parent_iid, state, item, matches[0])
            return
        if item["creation_submitted"]:
            if item["reason"] != UNKNOWN_CREATION:
                item["reason"] = UNKNOWN_CREATION
                self.client.save_fixture_state(parent_iid, state)
            logger.warning(
                "Issue #%s: the dependency child was submitted but cannot be found; holding "
                "the pause until it appears or an operator resets the item.", parent_iid,
            )
            return

        item["creation_submitted"] = True
        self.client.save_fixture_state(parent_iid, state)
        title, description = self._child_issue(parent_iid, state["project_id"], item)
        try:
            child = self.client.create_issue(title, description, labels=[self.client.issue_label])
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Issue #%s: creating the dependency child failed or its outcome is unknown: %s",
                parent_iid, exc,
            )
            item["reason"] = UNKNOWN_CREATION
            try:
                self.client.save_fixture_state(parent_iid, state)
            except Exception as save_exc:  # pylint: disable=broad-except
                logger.error("Issue #%s: could not record the unknown outcome: %s",
                             parent_iid, save_exc)
            telegram_notify(
                f"⚠️ Issue <b>#{parent_iid}</b> is paused, but creating its dependency issue "
                f"failed or its outcome is unknown: <code>{exc}</code>"
            )
            return
        logger.info("Issue #%s: opened dependency issue #%s (%s).",
                    parent_iid, child["iid"], child.get("web_url", ""))
        telegram_notify(
            f"🔗 Issue <b>#{parent_iid}</b> paused; opened dependency issue "
            f"<b>#{child['iid']}</b> – <i>{title}</i>"
        )
        self._link(parent_iid, state, item, child)

    def _link(self, parent_iid: int, state: dict, item: dict, child: dict) -> None:
        item["child_iid"] = child["iid"]
        item["state"] = "waiting"
        item["reason"] = ""
        self.client.save_fixture_state(parent_iid, state)
        if child.get("state") == "closed":
            self._observe_merge(parent_iid, state, item)
        if child.get("state") == "opened" and self.client.issue_label not in (child.get("labels") or []):
            logger.warning(
                "Dependency issue #%s of #%s is not opted in (%r missing); Nesti will not work "
                "on it and keeps #%s paused until a qualifying merge request is merged.",
                child["iid"], parent_iid, self.client.issue_label, parent_iid,
            )

    def _owned_children(
        self, parent_iid: int, project_id: int, item: dict
    ) -> tuple[list[dict], list[int]]:
        """
        Every issue (any state, any labels) whose trusted ownership marker
        matches *item* exactly, plus trusted issues whose marker names the key
        but does not validate.
        """
        owner = self.client.current_user_id()
        matches: list[dict] = []
        corrupt: list[int] = []
        for issue in self.client.list_issues(state="all"):
            description = issue.get("description") or ""
            if CHILD_MARKER not in description:
                continue
            if issue.get("author_id") != owner:
                logger.warning(
                    "Ignoring a dependency ownership marker on issue #%s: it was not authored "
                    "by the automation user.", issue["iid"],
                )
                continue
            try:
                marker = parse_child_marker(description)
            except ValueError as exc:
                if item["key"] in description:
                    corrupt.append(issue["iid"])
                logger.warning("Issue #%s carries an invalid ownership marker: %s", issue["iid"], exc)
                continue
            if marker is None or marker["key"] != item["key"]:
                continue
            if (marker["project_id"] == project_id and marker["parent_iid"] == parent_iid
                    and marker["target_branch"] == item["target_branch"]
                    and marker["requirement"] == item["requirement"]):
                matches.append(issue)
            else:
                corrupt.append(issue["iid"])
        return matches, corrupt

    def _child_issue(self, parent_iid: int, project_id: int, item: dict) -> tuple[str, str]:
        """The child's title and English backend description, built without an LLM."""
        requirement = item["requirement"]
        seeder, model = requirement["seeder"], requirement["model"]
        endpoint, table = requirement["endpoint"], requirement["table"]
        seeder_file = _class_path(seeder, SEEDER_PREFIX, "database/seeders")
        factory_file = f"database/factories/{_short_name(model)}Factory.php"
        title = (
            f"Add {_short_name(seeder)} for GET {endpoint} (dependency of #{parent_iid})"
        )[:_TITLE_MAX_CHARS]
        marker = format_child_marker(
            item["key"], project_id, parent_iid, item["target_branch"], requirement
        )
        description = "\n".join((
            "Scope: backend",
            "",
            f"Nesti paused #{parent_iid}: its end-to-end test needs real `{model}` rows from "
            f"`GET {endpoint}`, and the seeder it declared does not exist yet.",
            "",
            f"Evidence from the E2E sandbox at base commit `{item['base_sha']}`:",
            f"- After migrations and `DatabaseSeeder`, `GET {endpoint}` returned HTTP 200 with "
            "an empty collection.",
            f"- The `{table}` table holds no rows.",
            f"- Neither the class `{seeder}` nor the file `{seeder_file}` exists.",
            "",
            "Requirements:",
            f"- A Faker-backed model factory for `{model}`; reuse `{factory_file}` when it "
            "already exists.",
            f"- `{seeder}` in `{seeder_file}`, creating realistic `{model}` rows through that "
            "factory.",
            f"- Register `{seeder}` in `DatabaseSeeder::run()`.",
            f"- A PHPUnit Feature test proving that seeding creates `{model}` rows and that "
            f"`GET {endpoint}` then returns them.",
            "- No other API, schema or frontend changes.",
            "",
            "Acceptance Criteria:",
            f"- After `php artisan migrate --seed` the `{table}` table is not empty.",
            f"- `GET {endpoint}` returns at least one record after seeding.",
            "",
            f"Nesti resumes #{parent_iid} automatically once the merge request for this issue "
            f"is merged into `{item['target_branch']}`.",
            "",
            marker,
        ))
        return title, description

    # ------------------------------------------------------------------
    # Reconcile (every poll, before pending selection)
    # ------------------------------------------------------------------

    def reconcile(self) -> dict:
        """
        Advance every open opted-in issue's dependency record; no LLM calls.

        Returns ``{"resumed": [iid], "waiting": [iid], "errors": [{"issue_id",
        "error"}]}``.  A failure on one issue skips only that issue; a failure
        to list the issues raises, which aborts the poll.
        """
        summary: dict = {"resumed": [], "waiting": [], "errors": []}
        for issue in self.client.list_issues(state="opened", labels=[self.client.issue_label]):
            iid = issue["iid"]
            try:
                outcome = self._reconcile_issue(issue)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Dependency reconciliation of issue #%s failed: %s", iid, exc)
                summary["errors"].append({"issue_id": iid, "error": str(exc)})
                continue
            if outcome:
                summary[outcome].append(iid)
        return summary

    def _reconcile_issue(self, issue: dict) -> str:
        """Return "resumed", "waiting" or "" (no active record)."""
        iid = issue["iid"]
        state = self.client.get_fixture_state(iid)
        if not active_dependency(state):
            # No record, or a released one: a live lock or a later manual
            # pause on this issue is none of this workflow's business.
            return ""
        if state["project_id"] != issue.get("project_id"):
            raise RuntimeError(
                f"the dependency record names project {state['project_id']}, the issue "
                f"belongs to project {issue.get('project_id')}"
            )
        for item in state["items"]:
            if item["target_branch"] != self.target_branch:
                raise RuntimeError(
                    f"dependency {item['key'][:12]} targets {item['target_branch']!r} but the "
                    f"configured target branch is {self.target_branch!r}; the parent stays "
                    "paused until an operator migrates the record"
                )

        if not state["release_pending"]:
            items = state["items"]
            if (any(item["state"] == "creating" for item in items)
                    and self.client.pause_label not in (issue.get("labels") or [])):
                # The intent was recorded but the pause never applied.
                self._pause(iid, next(i for i in items if i["state"] == "creating")["requirement"])
            for item in items:
                if item["state"] == "creating":
                    self._advance_creating(iid, state, item)
                elif item["state"] == "waiting":
                    self._observe_merge(iid, state, item)
            if any(item["state"] != "merged" for item in items):
                return "waiting"
            if not state["release_pending"]:
                state["release_pending"] = True
                self.client.save_fixture_state(iid, state)

        current = self.client.get_issue(iid)
        if not self._open_and_opted_in(current):
            logger.info(
                "Issue #%s is no longer open and opted in; its dependencies are merged but it is "
                "left untouched.", iid,
            )
            return ""
        if not self.client.resume_issue(iid):
            raise RuntimeError("the parent could not be resumed (read-back did not confirm it)")
        state["release_pending"] = False
        self.client.save_fixture_state(iid, state)
        logger.info("Issue #%s resumed: every fixture dependency is merged.", iid)
        telegram_notify(f"▶️ Issue <b>#{iid}</b> resumed: its fixture dependencies are merged.")
        return "resumed"

    def _observe_merge(self, parent_iid: int, state: dict, item: dict) -> None:
        """waiting → merged only for a merged MR that closes the child on the recorded target."""
        child_iid = item["child_iid"]
        child = self.client.get_issue(child_iid)
        if child.get("state") == "opened" and self.client.issue_label not in (child.get("labels") or []):
            logger.warning(
                "Dependency issue #%s of #%s was opted out; #%s keeps waiting for a merged MR.",
                child_iid, parent_iid, parent_iid,
            )
        merged = self._qualifying_merge(child_iid, state["project_id"], item["target_branch"])
        if merged is None:
            if child.get("state") == "closed":
                logger.warning(
                    "Dependency issue #%s of #%s is closed without a merged MR that closes it on "
                    "%r; #%s stays paused.", child_iid, parent_iid, item["target_branch"], parent_iid,
                )
            return
        item["state"] = "merged"
        item["mr_iid"] = merged["iid"]
        item["merge_sha"] = _commit_sha(merged)
        item["reason"] = ""
        # The last merge and release intent must be one durable write. A
        # crash between separate notes would look like an already released
        # record and leave its pause label stranded forever.
        if all(entry["state"] == "merged" for entry in state["items"]):
            state["release_pending"] = True
        self.client.save_fixture_state(parent_iid, state)
        logger.info("Dependency issue #%s of #%s merged by !%s.", child_iid, parent_iid, merged["iid"])

    def _qualifying_merge(self, child_iid: int, project_id: int, target_branch: str) -> dict | None:
        candidates: list[tuple[datetime, int, dict]] = []
        for related in self.client.get_related_merge_requests(child_iid):
            if (type(related.get("project_id")) is not int or related["project_id"] != project_id
                    or type(related.get("iid")) is not int or related["iid"] <= 0):
                continue
            if not _closes_line(related.get("description"), child_iid):
                continue
            detail = self.client.get_merge_request(related["iid"])
            merged_at = _merged_at(detail.get("merged_at"))
            if (type(detail.get("iid")) is int and detail["iid"] == related["iid"]
                    and detail.get("state") == "merged" and merged_at is not None
                    and type(detail.get("target_project_id")) is int
                    and detail.get("target_project_id") == project_id
                    and detail.get("target_branch") == target_branch
                    and _closes_line(detail.get("description"), child_iid)):
                candidates.append((merged_at, detail["iid"], detail))
        if not candidates:
            return None
        return max(candidates, key=lambda entry: (entry[0], entry[1]))[2]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _open_and_opted_in(self, issue: dict) -> bool:
        return issue.get("state") == "opened" and self.client.issue_label in (issue.get("labels") or [])

    @staticmethod
    def _describe(item: dict) -> str:
        requirement = item["requirement"]
        what = f"GET {requirement['endpoint']} needs {requirement['seeder']}"
        if item["state"] == "waiting":
            return f"Paused until dependency issue #{item['child_iid']} is merged ({what})."
        if item["reason"]:
            return f"Paused: {item['reason']} ({what})."
        return f"Paused ({what})."
