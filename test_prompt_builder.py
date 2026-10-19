"""Offline prompt composition, budget visibility and measurement regressions."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

import prompt_builder as prompts
from skill_loader import Skill


ISSUE = {"id": 31, "subject": "Add TitleLength", "description": "Show title length; keep the API unchanged."}
BUILDERS = (
    ("plan", prompts.build_plan_prompt, (ISSUE,)),
    ("code", prompts.build_code_prompt, (ISSUE, "SCOPE: frontend\nAdd the column and its tests.")),
)


def chunk(body: str, title: str = "Reference", score: float = 0.9) -> dict:
    """Make an indexed passage with the same context prefix as real retrieval."""
    return {
        "doc_title": title, "heading": "Details", "doc_url": f"https://example.test/{title}",
        "text": f"# {title}\n## Details\n\n{body}", "score": score,
    }


class PromptBuilderTests(unittest.TestCase):
    def test_metrics_match_actual_sections_and_do_not_change_prompts(self) -> None:
        catalog = [Skill("https://example.test/catalog", "catalog passage", "Catalog")]
        skills = [Skill("https://example.test/issue", "issue guidance", "Issue skill")]
        chunks = [chunk("catalog passage", "Duplicate"), chunk("rendered passage")]
        source = deepcopy((catalog, skills, chunks))
        repo = "resources/js/components/Table.vue\nconst label = 'başlık';\n  // retain indentation\n"
        with patch.dict(os.environ, {"INCLUDE_SKILLS_IN_CODE_PROMPT": "1"}):
            for phase, builder, args in BUILDERS:
                for scope in prompts.SCOPES:
                    with self.subTest(phase=phase, scope=scope):
                        kwargs = dict(catalog_skills=catalog, skills=skills, retrieved_chunks=chunks,
                                      repo_context=repo, scope=scope)
                        if phase == "plan":
                            kwargs["past_solutions"] = [{"issue_id": 1, "plan": "Use the existing component."}]
                        else:
                            kwargs["recalled_failures"] = [{"attempt": 1, "layer": "vitest", "summary": "Expected 4, received 0"}]
                        expected = builder(*args, **kwargs)
                        metrics = {}
                        actual = builder(*args, metrics=metrics, **kwargs)
                        self.assertEqual(actual, expected)
                        system, user = actual
                        self.assertEqual(metrics["system_chars"], len(system))
                        self.assertEqual(metrics["user_chars"], len(user))
                        self.assertEqual(sum(value for name, value in metrics.items()
                                             if name.endswith("_chars") and name not in {"system_chars", "user_chars"}), len(user))
                        catalog_text = prompts.format_catalog_for_prompt(catalog, phase, scope)
                        self.assertIn(catalog_text, user)
                        self.assertEqual(metrics["catalog_chars"], len(catalog_text))
                        repo_text = f"\n## Existing Repository State\n{repo.strip()}\n"
                        self.assertIn(repo_text, user)
                        self.assertEqual(metrics["repo_chars"], len(repo_text))
                        rag_text = prompts._format_retrieved_section(
                            chunks, prompts._QDRANT_PLAN_BUDGET if phase == "plan" else prompts._QDRANT_CODE_BUDGET,
                            exclude_text=catalog_text,
                        )
                        self.assertIn(rag_text, user)
                        self.assertEqual(metrics["rag_chars"], len(rag_text))
                        self.assertEqual(metrics["rag_selected"], 2)
                        self.assertEqual(metrics["rag_rendered"], 1)
                        self.assertGreater(metrics["skills_chars"], 0)
        self.assertEqual((catalog, skills, chunks), source)

    def test_catalog_budget_omission_remains_eligible_for_rag(self) -> None:
        for phase, builder, args in BUILDERS:
            with self.subTest(phase=phase):
                budget = prompts._CATALOG_PLAN_BUDGET if phase == "plan" else prompts._CATALOG_CODE_BUDGET
                catalog = [
                    Skill("https://example.test/large", "visible passage\n" + "x" * budget, "Large"),
                    Skill("https://example.test/omitted", "omitted catalog passage", "Omitted"),
                ]
                chunks = [chunk("visible passage", "Large"), chunk("omitted catalog passage", "Omitted")]
                rendered_catalog = prompts.format_catalog_for_prompt(catalog, phase, "frontend")
                self.assertIn("visible passage", rendered_catalog)
                self.assertNotIn("omitted catalog passage", rendered_catalog)
                eligible = prompts.drop_injected_chunks(chunks, rendered_catalog)
                self.assertEqual(eligible, [chunks[1]])
                metrics = {}
                _, user = builder(*args, catalog_skills=catalog, retrieved_chunks=eligible,
                                  scope="frontend", metrics=metrics)
                self.assertIn(rendered_catalog, user)
                self.assertIn("omitted catalog passage", user)
                self.assertEqual(metrics["rag_selected"], 1)
                self.assertEqual(metrics["rag_rendered"], 1)

    def test_catalog_visibility_is_phase_specific(self) -> None:
        catalog = [
            Skill("https://example.test/large", "x" * 14_100, "Large"),
            Skill("https://example.test/last", "planning-only catalog passage", "Last"),
        ]
        passage = chunk("planning-only catalog passage", "Last")
        plan_catalog = prompts.format_catalog_for_prompt(catalog, "plan", "frontend")
        code_catalog = prompts.format_catalog_for_prompt(catalog, "code", "frontend")
        self.assertIn("planning-only catalog passage", plan_catalog)
        self.assertNotIn("planning-only catalog passage", code_catalog)
        self.assertEqual(prompts.drop_injected_chunks([passage], plan_catalog), [])
        self.assertEqual(prompts.drop_injected_chunks([passage], code_catalog), [passage])

    def test_rendered_count_excludes_duplicate_empty_and_oversized_passages(self) -> None:
        chunks = [
            chunk("x" * 7_000, "Oversized", 1.0), chunk("duplicate", "Duplicate"),
            chunk("", "Empty"), chunk("complete small passage", "Small", 0.1),
        ]
        for phase, builder, args in BUILDERS:
            with self.subTest(phase=phase):
                metrics = {"rag_selected": 99, "rag_rendered": 99}
                _, user = builder(*args, catalog_skills=[Skill("https://example.test/dup", "duplicate", "Catalog")],
                                  retrieved_chunks=chunks, metrics=metrics)
                self.assertEqual(metrics["rag_selected"], 4)
                self.assertEqual(metrics["rag_rendered"], 1)
                self.assertIn("complete small passage", user)
                self.assertNotIn("### Oversized", user)
                self.assertNotIn("### Duplicate", user)
                self.assertNotIn("### Empty", user)
                builder(*args, metrics=metrics)
                self.assertEqual(metrics["rag_selected"], 0)
                self.assertEqual(metrics["rag_rendered"], 0)
                self.assertEqual(metrics["rag_chars"], 0)
                self.assertEqual(metrics["catalog_chars"], 0)

    def test_rerank_order_survives_budget_skips_and_counting(self) -> None:
        chunks = [chunk("x" * 7_000, "Oversized"), chunk("second", "Second", 0.1), chunk("third", "Third", 0.9)]
        for index, item in enumerate(chunks):
            item.update(rerank_model="pinned-test-model", rerank_score=3 - index)
        for phase, builder, args in BUILDERS:
            with self.subTest(phase=phase):
                metrics = {}
                _, user = builder(*args, retrieved_chunks=chunks, metrics=metrics)
                self.assertLess(user.index("### Second"), user.index("### Third"))
                self.assertEqual(metrics["rag_selected"], 3)
                self.assertEqual(metrics["rag_rendered"], 2)


if __name__ == "__main__":
    unittest.main()
