"""Project isolation, verified legacy import and retrieval metadata regressions."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import redis

import conversation_store
import semantic_cache
import skill_catalog
import vector_store
from project_context import project_namespace


class ProjectMemoryTests(unittest.TestCase):
    """Exercise public memory APIs without network services or model downloads."""

    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {
            "GITLAB_URL": "https://gitlab.example.test",
            "GITLAB_PROJECT_PATH": "group/project",
            "CONVERSATION_TTL_DAYS": "7",
            "NESTI_SOLUTION_TTL_DAYS": "90",
            "NESTI_SOLUTION_MIN_SCORE": "0.8",
            "NESTI_EPISODE_MIN_SCORE": "0.6",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.embedder = MagicMock(enabled=True, available=True, dim=2)
        self.embedder.embed_documents.return_value = [[0.25, 0.75]]
        self.embedder.embed_query.return_value = [0.25, 0.75]
        embed = patch("semantic_cache.get_embedder", return_value=self.embedder)
        embed.start()
        self.addCleanup(embed.stop)
        connection = patch("redis.from_url")
        self.redis_factory = connection.start()
        self.addCleanup(connection.stop)
        self.redis = self.redis_factory.return_value
        self.memory = semantic_cache.SemanticMemory()

    def test_namespaces_separate_indices_writes_and_deletion(self) -> None:
        first = self.memory
        self.assertEqual(first.namespace, project_namespace())
        with patch.dict(os.environ, {"GITLAB_PROJECT_PATH": "group/other"}):
            second = semantic_cache.SemanticMemory()
        self.assertNotEqual(first.namespace, second.namespace)
        for memory in (first, second):
            schemas = memory._index_schemas(2)
            self.assertEqual(schemas[0][:2], (
                f"nesti_solution_{memory.namespace}_idx",
                f"nesti:memory:{memory.namespace}:solution:",
            ))
            self.assertEqual(schemas[1][:2], (
                f"nesti_episode_{memory.namespace}_idx",
                f"nesti:memory:{memory.namespace}:episode:",
            ))
            self.assertTrue(memory.remember_solution(7, "subject", "description", "plan", "php", "url"))
            pipe = self.redis.pipeline.return_value
            self.assertEqual(pipe.hset.call_args.args[0], memory.solution_prefix + "7")
            self.assertEqual(pipe.expire.call_args.args, (memory.solution_prefix + "7", 90 * 86400))
            self.assertTrue(memory.remember_failure(7, 1, "PHPUnit", "failure"))
            episode = memory.episode_prefix + "7:1:phpunit"
            self.assertEqual(pipe.hset.call_args.args[0], episode)
            self.assertEqual(pipe.expire.call_args.args, (episode, 7 * 86400))
            self.redis.keys.return_value = [episode]
            self.redis.delete.return_value = 1
            self.assertEqual(memory.forget_episodes(7), 1)
            self.redis.keys.assert_called_with(memory.episode_prefix + "7:*")
            self.redis.delete.assert_called_with(episode)
            self.assertEqual(memory.status()["namespace"], memory.namespace)
        self.redis_factory.assert_called_with(
            self.memory._url, decode_responses=False, socket_connect_timeout=3,
        )

    def test_conversations_isolate_identical_iids_in_redis_and_fallback(self) -> None:
        for fallback in (False, True):
            with self.subTest(fallback=fallback):
                self.redis_factory.side_effect = ConnectionError("offline") if fallback else None
                first = conversation_store.ConversationStore()
                with patch.dict(os.environ, {"GITLAB_PROJECT_PATH": "group/other"}):
                    second = conversation_store.ConversationStore()
                data = {"ai-dev:issue:7:messages": '[{"role":"user","content":"legacy"}]'}
                if fallback:
                    first._memory = second._memory = data
                else:
                    self.redis.set.side_effect = lambda key, value, **kwargs: data.__setitem__(key, value)
                    self.redis.get.side_effect = data.get
                    self.redis.delete.side_effect = lambda key: data.pop(key, None)
                    self.redis_factory.assert_called_with(
                        os.getenv("REDIS_URL", "redis://nesti-redis:6379/0"),
                        decode_responses=True, socket_connect_timeout=3,
                    )
                self.assertEqual(first.load(7), [])
                first.append(7, "user", "first")
                second.append(7, "user", "second")
                self.assertEqual(first.load(7)[0]["content"], "first")
                self.assertEqual(second.load(7)[0]["content"], "second")
                first.delete(7)
                self.assertEqual(first.load(7), [])
                self.assertEqual(second.load(7)[0]["content"], "second")
                self.assertIn("ai-dev:issue:7:messages", data)

    def test_missing_or_invalid_identity_disables_all_private_memory(self) -> None:
        for identity in ({"GITLAB_PROJECT_PATH": ""}, {"GITLAB_URL": "not-a-url"}):
            with self.subTest(identity=identity), patch.dict(os.environ, identity):
                self.redis_factory.reset_mock()
                memory = semantic_cache.SemanticMemory()
                history = conversation_store.ConversationStore()
                self.assertFalse(memory.available)
                self.assertFalse(history.available)
                self.assertEqual(history.append(7, "user", "private"), [])
                history.save(7, [{"role": "user", "content": "private"}])
                history.delete(7)
                self.assertEqual(history._memory, {})
                self.assertEqual(history.load(7), [])
                self.assertEqual(memory.find_similar_solutions("private"), [])
                self.assertEqual(memory.recall_failures(7, "private", 3), [])
                self.assertFalse(memory.remember_solution(7, "s", "d", "p", "php", "u"))
                self.assertFalse(memory.remember_failure(7, 1, "PHPUnit", "output"))
                self.assertEqual(memory.forget_episodes(7), 0)
                self.assertFalse(memory.migrate_legacy_solutions()["available"])
                self.assertIsNone(memory.status()["solutions"])
                self.redis_factory.assert_not_called()

    def test_retrieval_uses_only_project_indices_and_returns_age(self) -> None:
        document = SimpleNamespace(issue_id=b"7", subject=b"subject", plan=b"plan",
                                   mr_url=b"url", stack=b"php", attempt=b"1",
                                   layer=b"PHPUnit", summary=b"failure", created_at=b"123", score=b"0.1")
        self.redis.ft.return_value.search.return_value.docs = [document]
        self.assertEqual(self.memory.find_similar_solutions("query")[0]["created_at"], 123)
        self.redis.ft.assert_called_with(self.memory.solution_index)
        self.assertEqual(self.memory.recall_failures(7, "query", 3)[0]["created_at"], 123)
        self.redis.ft.assert_called_with(self.memory.episode_index)
        query = self.redis.ft.return_value.search.call_args.args[0]
        self.assertIn("@issue_id:[7 7] @attempt:[-inf 1]", query.query_string())
        self.assertEqual(self.memory.recall_failures(7, "query", 2), [])

    def _legacy(self) -> tuple[bytes, dict]:
        return b"nesti:memory:solution:7", {
            b"issue_id": b"7", b"subject": b"old subject", b"plan": b"old plan",
            b"mr_url": b"https://gitlab.example.test/group/project/-/merge_requests/12",
            b"created_at": b"123", b"stack": b"php", b"embedding": b"obsolete-vector",
        }

    def _migration_client(self) -> MagicMock:
        client = MagicMock(base_url="https://gitlab.example.test", project_path="group/project")
        client.get_project.return_value = {"id": 10, "path_with_namespace": "group/project"}
        client.get_merge_request.return_value = {
            "project_id": 10, "iid": 12,
            "web_url": "https://gitlab.example.test/group/project/-/merge_requests/12",
            "state": "opened",
        }
        key, record = self._legacy()
        self.redis.scan_iter.return_value = [key]
        self.redis.hgetall.return_value = record
        self.redis.exists.return_value = False
        self.redis.eval.return_value = 1
        return client

    def test_verified_migration_reembeds_without_claiming_merge(self) -> None:
        client = self._migration_client()
        key, record = self._legacy()
        with patch("gitlab_issues_client.GitLabIssuesClient", return_value=client):
            result = self.memory.migrate_legacy_solutions()
        self.assertEqual(result, {"available": True, "migrated": 1, "skipped": 0, "reason": ""})
        client.get_project.assert_called_once_with()
        client.get_merge_request.assert_called_once_with(12)
        self.redis.scan_iter.assert_called_once_with(match="nesti:memory:solution:*", count=100)
        self.embedder.embed_documents.assert_called_once_with(["old subject\nold plan"])
        self.redis.eval.assert_called_once_with(
            semantic_cache._MIGRATE_SOLUTION, 2, key, self.memory.solution_prefix + "7",
            semantic_cache._to_blob([0.25, 0.75]),
            *[item for pair in record.items() for item in pair],
        )
        self.redis.delete.assert_not_called()

    def test_wrong_project_credentials_and_unverified_records_are_skipped(self) -> None:
        for change in (
            {b"mr_url": b"https://gitlab.example.test/group/other/-/merge_requests/12"},
            {b"mr_url": b"https://token@gitlab.example.test/group/project/-/merge_requests/12"},
            {b"mr_url": b"https://other.test/group/project/-/merge_requests/12"},
            {b"issue_id": b"8"},
        ):
            with self.subTest(change=change):
                client = self._migration_client()
                self.redis.hgetall.return_value.update(change)
                with patch("gitlab_issues_client.GitLabIssuesClient", return_value=client):
                    result = self.memory.migrate_legacy_solutions()
                self.assertEqual((result["available"], result["skipped"]), (True, 1))
                client.get_merge_request.assert_not_called()
                self.redis.eval.assert_not_called()
        for change in ({"project_id": 11}, {"iid": 13}, {"web_url": "https://other.test/mr/12"}):
            with self.subTest(change=change):
                client = self._migration_client()
                client.get_merge_request.return_value.update(change)
                with patch("gitlab_issues_client.GitLabIssuesClient", return_value=client):
                    result = self.memory.migrate_legacy_solutions()
                self.assertEqual(result["skipped"], 1)
                self.redis.eval.assert_not_called()

    def test_migration_outages_preserve_originals_and_report_unavailable(self) -> None:
        for failure in ("project", "mr", "embedding", "redis"):
            with self.subTest(failure=failure):
                client = self._migration_client()
                self.redis.eval.reset_mock(side_effect=True)
                self.embedder.embed_documents.return_value = [[0.25, 0.75]]
                if failure == "project":
                    client.get_project.side_effect = ConnectionError("offline")
                elif failure == "mr":
                    client.get_merge_request.side_effect = ConnectionError("offline")
                elif failure == "embedding":
                    self.embedder.embed_documents.return_value = []
                else:
                    self.redis.eval.side_effect = ConnectionError("offline")
                with patch("gitlab_issues_client.GitLabIssuesClient", return_value=client):
                    result = self.memory.migrate_legacy_solutions()
                self.assertFalse(result["available"])
                self.assertTrue(result["reason"])
                self.redis.delete.assert_not_called()

    def test_existing_destination_and_identity_mismatch_never_write(self) -> None:
        client = self._migration_client()
        self.redis.exists.return_value = True
        with patch("gitlab_issues_client.GitLabIssuesClient", return_value=client):
            self.assertEqual(self.memory.migrate_legacy_solutions()["skipped"], 1)
            client.get_merge_request.assert_not_called()
            with patch.dict(os.environ, {"GITLAB_PROJECT_PATH": "group/other"}):
                self.assertFalse(self.memory.migrate_legacy_solutions()["available"])
            client.get_project.return_value["path_with_namespace"] = "group/other"
            self.assertFalse(self.memory.migrate_legacy_solutions()["available"])
        self.redis.eval.assert_not_called()

    def test_startup_adapter_delegates(self) -> None:
        with patch("semantic_cache.get_semantic_memory", return_value=self.memory), \
                patch.object(self.memory, "migrate_legacy_solutions", return_value={"available": False}) as migrate:
            self.assertEqual(semantic_cache.migrate_legacy_solutions(), {"available": False})
        migrate.assert_called_once_with()

    def test_shared_document_and_catalog_metadata(self) -> None:
        docs = vector_store.DocumentMemory.__new__(vector_store.DocumentMemory)
        docs._collection = "shared_docs"
        docs._client = MagicMock()
        docs._client.query_points.return_value.points = [SimpleNamespace(
            score=0.9, payload={"version": "13.x", "doc_hash": "hash", "chunk_index": 2},
        )]
        for project in ("group/project", "group/other", ""):
            with patch.dict(os.environ, {"GITLAB_PROJECT_PATH": project}):
                hit = docs._query([0.25, 0.75], "php", 1)[0]
                self.assertEqual((hit["version"], hit["doc_hash"], hit["chunk_index"]), ("13.x", "hash", 2))
                self.assertEqual(docs._client.query_points.call_args.kwargs["collection_name"], "shared_docs")
        with patch("skill_catalog.load_registry", return_value={"generated_at": "2026-10-01T00:00:00Z"}):
            self.assertEqual(skill_catalog.catalog_status()["generated_at"], "2026-10-01T00:00:00Z")
        with patch("skill_catalog.load_registry", return_value={}):
            self.assertIsNone(skill_catalog.catalog_status()["generated_at"])


@unittest.skipUnless(shutil.which("redis-server"), "redis-server needed for atomic Lua regression")
class AtomicLegacyMigrationTests(unittest.TestCase):
    """Run the real copy script against an isolated, nonpersistent Unix-socket Redis."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="nesti-memory-test-")
        self.addCleanup(directory.cleanup)
        socket = os.path.join(directory.name, "redis.sock")
        process = subprocess.Popen([
            shutil.which("redis-server"), "--port", "0", "--unixsocket", socket,
            "--save", "", "--appendonly", "no", "--dir", directory.name,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def stop() -> None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        self.addCleanup(stop)
        self.redis = redis.Redis(unix_socket_path=socket, socket_timeout=1)
        self.addCleanup(self.redis.close)
        deadline = time.monotonic() + 5
        while True:
            try:
                self.redis.ping()
                break
            except redis.ConnectionError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    self.fail("isolated Redis failed to start")
                time.sleep(0.01)
        self.source = "nesti:memory:solution:7"
        self.destination = "nesti:memory:project:solution:7"
        self.record = {b"issue_id": b"7", b"subject": b"old", b"created_at": b"123", b"embedding": b"old"}
        self.redis.hset(self.source, mapping=self.record)

    def _copy(self) -> int:
        return self.redis.eval(
            semantic_cache._MIGRATE_SOLUTION, 2, self.source, self.destination, b"new-vector",
            *[item for pair in self.record.items() for item in pair],
        )

    def test_copy_preserves_age_ttl_source_and_repeat_safety(self) -> None:
        self.redis.pexpire(self.source, 60000)
        before = self.redis.pttl(self.source)
        self.assertEqual(self._copy(), 1)
        copied = self.redis.hgetall(self.destination)
        self.assertEqual(copied, self.record | {b"embedding": b"new-vector"})
        self.assertLessEqual(self.redis.pttl(self.destination), before)
        self.assertLessEqual(abs(self.redis.pttl(self.source) - self.redis.pttl(self.destination)), 100)
        self.assertEqual(self.redis.hgetall(self.source), self.record)
        self.redis.hset(self.destination, "subject", "newer")
        self.assertEqual(self._copy(), 0)
        self.assertEqual(self.redis.hget(self.destination, "subject"), b"newer")

    def test_changed_expired_or_deleted_sources_are_not_imported(self) -> None:
        self.redis.hset(self.source, "subject", "changed")
        self.assertEqual(self._copy(), -1)
        self.assertFalse(self.redis.exists(self.destination))
        self.redis.delete(self.source)
        self.assertEqual(self._copy(), -1)
        self.redis.hset(self.source, mapping=self.record)
        self.redis.pexpire(self.source, 0)
        self.assertEqual(self._copy(), -1)
        self.assertFalse(self.redis.exists(self.destination))

    def test_nonexpiring_source_stays_nonexpiring(self) -> None:
        self.assertEqual(self._copy(), 1)
        self.assertEqual(self.redis.pttl(self.destination), -1)


if __name__ == "__main__":
    unittest.main()
