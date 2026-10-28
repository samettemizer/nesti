"""Offline escalation protocol tests; no GitLab, Docker or model calls."""
import copy
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from git import Actor, Repo

import issue_escalations as service
from gitlab_issues_client import GitLabIssuesClient
from project_architecture import collect_inventory


class Response:
    def __init__(self, value, next_page=""):
        self.value = value
        self.headers = {"X-Next-Page": next_page}
        self.status_code = 201
        self.text = ""

    def json(self):
        return copy.deepcopy(self.value)

    def raise_for_status(self):
        pass


class GitLab:
    issue_label = "nesti"
    pause_label = "nesti::pause"
    in_progress_label = "nesti::in-progress"
    _project_api = "https://gitlab.example/api/v4/projects/group%2Fapp"

    def __init__(self):
        self.issues = {}
        self.notes = []
        self.events = []
        self.lose = set()
        self.drop = set()
        self.hold = None
        self.claim = False
        self.session = Mock()
        self.session.get.side_effect = self.get_note

    def get_project(self):
        return {"id": 42}

    def current_user_id(self):
        return 7

    def list_issues(self, *, state):
        assert state == "all"
        return copy.deepcopy(list(self.issues.values()))

    def get_issue(self, iid):
        return copy.deepcopy(self.issues[iid])

    def create_issue(self, title, description, labels=None):
        self.events.append("create")
        if "create" not in self.drop:
            iid = len(self.issues) + 1
            self.issues[iid] = {"id": iid, "iid": iid, "subject": title,
                                "description": description, "labels": labels,
                                "state": "opened", "project_id": 42,
                                "author_id": 7, "web_url": f"https://gitlab.example/group/app/-/issues/{iid}"}
        if "create" in self.lose or "create" in self.drop:
            raise TimeoutError("lost POST response")
        return self.get_issue(iid)

    def list_notes(self, iid):
        return copy.deepcopy(list(self.notes))

    def get_note(self, url, **kwargs):
        self.events.append("verify_note")
        return Response(next(note for note in self.notes if note["id"] == int(url.rsplit("/", 1)[1])))

    def _record_hold_reason(self, iid):
        return self.hold

    def _comment(self, iid, body):
        self.events.append("note")
        if "note" not in self.drop:
            self.notes.append({"id": len(self.notes) + 1, "body": body, "system": False,
                               "author": {"id": 7, "username": "automation"}})
        return "note" not in self.lose and "note" not in self.drop

    def close_issue(self, iid, note=""):
        assert note == ""
        self.events.append("close")
        if "close" not in self.drop:
            issue = self.get_issue(iid)
            issue["state"] = "closed"
            self.issues[iid] = issue
        return "close" not in self.lose and "close" not in self.drop

    def _update(self, iid, payload):
        event = "description" if "description" in payload else "label"
        self.events.append(event)
        issue = self.get_issue(iid)
        if event not in self.drop:
            if event == "description":
                issue["description"] = payload["description"]
            else:
                issue["labels"] += [payload["add_labels"]]
                if self.claim:
                    issue["labels"].append(self.in_progress_label)
            self.issues[iid] = issue
        if event in self.lose:
            raise TimeoutError("lost PUT response")
        return issue


def rejected(round_number):
    return {"round": round_number, "reviewer_id": "independent-reviewer",
            "verdict": "changes_requested", "must_fix": ["Preserve keyboard interaction"],
            "tests_run": ["Vitest: interaction failed"]}


def approve():
    return {"round": 3, "reviewer_id": "independent-reviewer", "verdict": "approve",
            "must_fix": [], "tests_run": ["Vitest and Playwright passed"]}


class EscalationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "app"
        self.root.mkdir()
        (self.root / "artisan").write_text("<?php // entry\n")
        (self.root / "composer.json").write_text('{"autoload":{"psr-4":{"App\\\\":"app/"}}}')
        (self.root / "app").mkdir()
        (self.root / "app/Example.php").write_text("<?php // original\n")
        (self.root / ".gitignore").write_text("ignored.php\n.env\n")
        self.repo = Repo.init(self.root)
        self.repo.index.add(["artisan", "composer.json", "app/Example.php", ".gitignore"])
        actor = Actor("Fixture", "fixture@example.test")
        self.repo.index.commit("fixture", author=actor, committer=actor)
        (self.root / "app/Example.php").write_text("<?php // rejected local edit\n")
        self.project = {"id": 42, "namespace": "project-namespace", "application_root": "",
                        "root": str(self.root), "git_root": str(self.root), "target_branch": "main",
                        "source": {"head": self.repo.head.commit.hexsha, "branch": self.repo.active_branch.name}}
        self.client = GitLab()
        self.operation = str(uuid4())
        self.report = {"title": "Keyboard interaction", "request": "Fix the existing frontend widget",
                       "acceptance_criteria": ["Keyboard-only users can activate the widget"], "scope": "frontend",
                       "source": {"application_root": "", "head": self.repo.head.commit.hexsha,
                                  "local_branch": self.repo.active_branch.name, "target_branch": "main"},
                       "changed_files": ["app/Example.php"], "reviews": [rejected(1), rejected(2)],
                       "workspace_evidence": {"tests": ["Vitest failure"], "prerequisites": []},
                       "architecture_fingerprint": collect_inventory(str(self.root))["fingerprint"]}
        for patcher in (patch.dict(os.environ, {"NESTI_STATE_DIR": str(Path(self.temp.name) / "state")}),
                        patch.object(service, "GitLabIssuesClient", return_value=self.client),
                        patch.object(service, "configured_project_root", return_value=self.root),
                        patch.object(service, "inspect_project", return_value=self.project),
                        patch.object(service, "project_namespace", return_value=self.project["namespace"])):
            patcher.start()
            self.addCleanup(patcher.stop)

    def create(self):
        return service.issue_escalation_create(42, self.operation, self.report)

    def complete(self):
        return service.issue_escalation_complete(42, 1, self.operation, "provider/actual-runtime-model", approve())

    def handoff_report(self):
        report = copy.deepcopy(self.report)
        report.update(reviews=[*report["reviews"], rejected(3)], advisor_summary="Restore the existing key handler",
                      tests_run=["Playwright: keyboard criterion failed"], transfer_mode="clean_reimplementation")
        return report

    def handoff(self):
        return service.issue_escalation_handoff(42, 1, self.operation, self.handoff_report())

    def test_split_project_capture_keeps_frontend_and_backend_evidence(self):
        backend = self.root / "backend"
        frontend = self.root / "frontend"
        backend.mkdir()
        frontend.mkdir()
        (backend / "Example.php").write_text("<?php // original API\n")
        (frontend / "App.vue").write_text("<template>original SPA</template>\n")
        self.repo.index.add(["backend/Example.php", "frontend/App.vue"])
        actor = Actor("Fixture", "fixture@example.test")
        self.repo.index.commit("split fixture", author=actor, committer=actor)
        (backend / "Example.php").write_text("<?php // changed API\n")
        (frontend / "App.vue").write_text("<template>changed SPA</template>\n")
        project = {**self.project, "root": str(backend), "project_root": str(self.root),
                   "application_root": "backend", "frontend_root": "frontend"}
        evidence = service._capture(project, {
            "changed_files": ["backend/Example.php", "frontend/App.vue"],
        })
        files = {item["path"]: item for item in evidence["files"]}
        self.assertEqual(set(files), {"backend/Example.php", "frontend/App.vue"})
        self.assertEqual(files["frontend/App.vue"]["kind"], "HEAD_diff")
        self.assertIn("-<template>original SPA</template>", files["frontend/App.vue"]["content"])
        self.assertIn("+<?php // changed API", files["backend/Example.php"]["content"])
        self.assertEqual(evidence["fingerprint"], collect_inventory(str(self.root))["fingerprint"])

    def test_create_is_unlabeled_idempotent_and_preserves_frontend_scope(self):
        first = self.create()
        self.assertTrue(first["success"], first)
        self.assertEqual(self.create(), first)
        self.assertEqual(self.client.events.count("create"), 1)
        self.assertEqual(self.client.issues[1]["labels"], [])
        description = self.client.issues[1]["description"]
        self.assertIn("Keyboard-only users", description)
        self.assertIn("pre-existing local edits", description)
        self.assertNotIn("PHPUnit", description)
        self.assertEqual(first["result"]["phase"], "assisted")

    def test_lost_creation_response_recovers_without_another_post(self):
        self.client.lose.add("create")
        self.assertTrue(self.create()["success"])
        self.assertTrue(self.create()["success"])
        self.assertEqual(self.client.events.count("create"), 1)

    def test_unaccepted_post_is_never_automatically_retried(self):
        self.client.drop.add("create")
        self.assertEqual(self.create()["code"], "creation_unconfirmed")
        self.client.drop.clear()
        self.assertEqual(self.create()["code"], "creation_unconfirmed")
        self.assertEqual(self.client.events.count("create"), 1)

    def test_conflicting_operation_and_project_are_rejected(self):
        self.assertTrue(self.create()["success"])
        self.report["request"] = "Different task"
        self.assertEqual(self.create()["code"], "operation_conflict")
        self.assertEqual(service.issue_escalation_create(99, str(uuid4()), self.report)["code"], "project_mismatch")

    def test_malformed_reports_never_submit(self):
        for change in ({"reviews": [rejected(2), rejected(1)]}, {"changed_files": ["../secret.php"]},
                       {"architecture_fingerprint": "not-a-hash"}, {"request": "NESTI_OMP_ESCALATION_V1"}):
            with self.subTest(change=change):
                report = {**self.report, **change}
                result = service.issue_escalation_create(42, str(uuid4()), report)
                self.assertEqual(result["code"], "invalid_report")
        self.assertEqual(self.client.events, [])

    def test_duplicate_trusted_owner_fails_but_foreign_marker_is_not_authority(self):
        self.assertTrue(self.create()["success"])
        duplicate = self.client.get_issue(1)
        duplicate.update(iid=2, id=2, author_id=999)
        self.client.issues[2] = duplicate
        self.assertTrue(self.create()["success"])
        duplicate["author_id"] = 7
        self.client.issues[2] = duplicate
        self.assertEqual(self.create()["code"], "ownership_mismatch")

    def test_complete_verifies_exact_note_before_close_and_is_idempotent(self):
        self.assertTrue(self.create()["success"])
        self.client.lose.update({"note", "close"})
        result = self.complete()
        self.assertTrue(result["success"], result)
        self.assertEqual(result["result"]["phase"], "completed")
        self.assertLess(self.client.events.index("verify_note"), self.client.events.index("close"))
        self.assertTrue(self.complete()["success"])
        self.assertEqual(self.client.events.count("note"), 1)
        self.assertEqual(self.client.events.count("close"), 1)
        self.assertEqual(self.handoff()["code"], "operation_conflict")

    def test_failed_note_never_closes_or_reposts(self):
        self.create()
        self.client.drop.add("note")
        self.assertEqual(self.complete()["code"], "transition_unconfirmed")
        self.client.drop.clear()
        self.assertEqual(self.complete()["code"], "transition_unconfirmed")
        self.assertEqual(self.client.events.count("note"), 1)
        self.assertNotIn("close", self.client.events)

    def test_foreign_or_system_attribution_cannot_close(self):
        self.create()
        body = "omp-developer / model: provider/actual-runtime-model"
        self.client.notes.extend([{"id": 1, "body": body, "system": False, "author": {"id": 999}},
                                  {"id": 2, "body": body, "system": True, "author": {"id": 7}}])
        self.client.drop.add("note")
        self.assertFalse(self.complete()["success"])
        self.assertNotIn("close", self.client.events)

    def test_manual_closure_pause_and_dependency_hold_are_preserved(self):
        self.create()
        for state, labels, hold in (("closed", [], None), ("opened", ["nesti::pause"], None),
                                    ("opened", [], "unresolved dependency")):
            with self.subTest(state=state, labels=labels, hold=hold):
                self.client.issues[1].update(state=state, labels=labels)
                self.client.hold = hold
                self.assertEqual(self.complete()["code"], "operation_conflict")
                self.assertEqual(self.handoff()["code"], "operation_conflict")
        self.assertEqual(self.client.events, ["create"])

    def test_handoff_preserves_description_labels_and_accepts_immediate_claim(self):
        self.create()
        original = self.client.issues[1]["description"]
        self.client.issues[1]["labels"] = ["human-triage"]
        self.client.claim = True
        self.client.lose.update({"description", "label"})
        result = self.handoff()
        self.assertTrue(result["success"], result)
        self.assertEqual(result["result"]["phase"], "handed_off")
        self.assertTrue(self.client.issues[1]["description"].startswith(original))
        self.assertEqual(self.client.issues[1]["labels"], ["human-triage", "nesti", "nesti::in-progress"])
        self.assertTrue(self.handoff()["success"])
        self.assertEqual(self.client.events.count("description"), 1)
        self.assertEqual(self.client.events.count("label"), 1)
        self.assertEqual(self.complete()["code"], "operation_conflict")

    def test_description_failure_never_enables_intake(self):
        self.create()
        self.client.drop.add("description")
        self.assertEqual(self.handoff()["code"], "transition_unconfirmed")
        self.client.drop.clear()
        self.assertEqual(self.handoff()["code"], "transition_unconfirmed")
        self.assertNotIn("label", self.client.events)

    def test_human_opt_out_after_submission_is_never_reversed(self):
        self.create()
        self.assertTrue(self.handoff()["success"])
        self.client.issues[1]["labels"] = []
        self.assertEqual(self.handoff()["code"], "transition_unconfirmed")
        self.assertEqual(self.client.events.count("label"), 1)

    def test_actual_developer_failure_is_allowed_but_infrastructure_is_not(self):
        self.create()
        report = self.handoff_report()
        report.update(reviews=self.report["reviews"], outcome="developer_failed",
                      failure_kind="infrastructure", failure_output="Model unavailable")
        self.assertEqual(service.issue_escalation_handoff(42, 1, self.operation, report)["code"], "invalid_report")
        report.update(failure_kind="execution", failure_output="Developer could not implement the required handler")
        result = service.issue_escalation_handoff(42, 1, self.operation, report)
        self.assertTrue(result["success"], result)

    def test_history_distinguishes_empty_unavailable_and_authenticated_notes(self):
        self.create()
        empty = service.issue_history(42, 1)
        self.assertTrue(empty["success"])
        self.assertEqual(empty["result"]["notes"], [])
        self.assertEqual(empty["result"]["escalation"]["operation_id"], self.operation)
        self.client.notes.extend([{"id": 1, "body": "human", "system": False, "author": {"id": 8}},
                                  {"id": 2, "body": "bot", "system": False, "author": {"id": 7}},
                                  {"id": 3, "body": "system", "system": True, "author": {"id": 7}}])
        notes = service.issue_history(42, 1)["result"]["notes"]
        self.assertEqual([note["trusted_automation"] for note in notes], [False, True, False])
        with patch.object(self.client, "list_notes", side_effect=TimeoutError("offline")):
            self.assertFalse(service.issue_history(42, 1)["success"])
        self.client.issues[1]["author_id"] = 999
        self.assertEqual(service.issue_history(42, 1)["code"], "ownership_mismatch")

    def test_reference_capture_omits_secrets_symlinks_binary_and_ignored_files(self):
        (self.root / "new.php").write_text("<?php // complete new source\n")
        (self.root / ".env").write_text("TOKEN=never-export")
        (self.root / "credentials.json").write_text('{"password":"never-export"}')
        (self.root / "ignored.php").write_text("never-export")
        (self.root / "binary.php").write_bytes(b"\x00never-export")
        (self.root / "link.php").symlink_to(self.root / ".env")
        (self.root / "large.php").write_text("<?php " + "x" * 100_001)
        report = {**self.report, "changed_files": ["app/Example.php", "new.php", ".env", "credentials.json", "ignored.php", "binary.php", "link.php", "missing.php", "large.php"]}
        evidence = service._capture(self.project, report)
        self.assertNotIn("never-export", service._json(evidence))
        files = {item["path"]: item for item in evidence["files"]}
        self.assertEqual(files["app/Example.php"]["kind"], "HEAD_diff")
        self.assertEqual(files["new.php"]["content"], "<?php // complete new source\n")
        self.assertEqual(files["missing.php"]["status"], "deleted/unavailable")
        self.assertEqual(len(evidence["omitted"]), 6)

    def test_completion_handoff_race_has_one_terminal_owner(self):
        self.create()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda fn: fn(), [self.complete, self.handoff]))
        self.assertEqual(sum(result["success"] for result in results), 1, results)
        self.assertFalse("close" in self.client.events and "label" in self.client.events)

    def test_separate_processes_submit_exactly_one_issue(self):
        context = multiprocessing.get_context("fork")
        with context.Manager() as manager:
            self.client.issues = manager.dict()
            self.client.events = manager.list()
            barrier = context.Barrier(2)
            results = context.Queue()

            def invoke():
                barrier.wait(timeout=10)
                results.put(self.create())

            processes = [context.Process(target=invoke) for _ in range(2)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=20)
                if process.is_alive():
                    process.terminate()
                    process.join()
                self.assertEqual(process.exitcode, 0)
            answers = [results.get(timeout=2) for _ in processes]
            self.assertTrue(all(answer["success"] for answer in answers), answers)
            self.assertEqual(list(self.client.events).count("create"), 1)
            results.close()


class GitLabTransportTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"GITLAB_URL": "https://gitlab.example", "GITLAB_TOKEN": "test-token", "GITLAB_PROJECT_PATH": "group/app"})
        environment.start()
        self.addCleanup(environment.stop)
        self.client = GitLabIssuesClient()
        self.client.session = Mock()

    def test_notes_and_all_state_issues_follow_every_page(self):
        pages = []

        def get(url, params, **kwargs):
            pages.append((params["page"], params.get("state")))
            page = int(params["page"])
            if url.endswith("/notes"):
                return Response([{"id": 4 - page}], str(page + 1) if page < 3 else "")
            return Response([{"iid": page, "project_id": 42}], str(page + 1) if page < 3 else "")

        self.client.session.get.side_effect = get
        self.assertEqual([note["id"] for note in self.client.list_notes(1)], [1, 2, 3])
        self.assertEqual([issue["iid"] for issue in self.client.list_issues(state="all")], [1, 2, 3])
        self.assertEqual(pages, [("1", None), ("2", None), ("3", None), ("1", "all"), ("2", "all"), ("3", "all")])

    def test_empty_labels_are_explicit_but_none_omits_field(self):
        self.client.session.post.return_value = Response({"iid": 1})
        self.client.session.get.return_value = Response({"iid": 1, "title": "Title", "description": "Body", "labels": []})
        self.client.create_issue("Title", "Body", labels=[])
        self.assertEqual(self.client.session.post.call_args.kwargs["json"]["labels"], "")
        self.client.create_issue("Title", "Body", labels=None)
        self.assertNotIn("labels", self.client.session.post.call_args.kwargs["json"])
        self.client.session.get.return_value = Response({"iid": 1, "title": "Title", "description": "Body", "labels": ["default-label"]})
        with self.assertRaises(RuntimeError):
            self.client.create_issue("Title", "Body", labels=[])

    def test_project_and_note_identity_are_validated(self):
        self.client.session.get.return_value = Response({"id": 42})
        self.assertEqual(self.client.get_project()["id"], 42)
        self.client.session.get.return_value = Response({"id": True})
        with self.assertRaises(RuntimeError):
            self.client.get_project()
        self.client.session.get.return_value = Response([{"id": True}])
        with self.assertRaises(RuntimeError):
            self.client.list_notes(1)


if __name__ == "__main__":
    unittest.main()
