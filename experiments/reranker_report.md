# PyTorch documentation reranker: implementation and decision

**Decision: not approved for activation.**

Reference: `.private/PLAN_NESTI_PYTORCH_DOCUMENTATION.md`, edition 3.0.
Branch: `feat/pytorch-documentation-reranker`.
Machine-readable verification: `experiments/reranker_report.json`.

## Delivered scope

- `reranker.py`: standalone, lazily imported CPU/FP32/SDPA scoring through the complete Sentence Transformers CrossEncoder. Raw finite scores preserve input positions. Real tokenizer encodings retain the first 96 and last 32 query tokens above 128; only the passage is then truncated to the pair budget. Candidate dictionaries and stored text are not changed. One resident model/configuration is reused per experiment process.
- `experiments/reranker_poc.py`: explicit-path `capture`, `evaluate`, `smoke`, and `compare` CLI commands. Capture is read-only; evaluation never queries Qdrant or calls an LLM. Models are local-only. Output artifacts are created with mode 0600 and existing files are never overwritten.
- `experiments/reranker_evaluation.py`: strict labeled-fixture validation; separate merged-lane/dense/neural ranking comparisons and legacy/expanded-dense/expanded-neural selection comparisons; six-slot lane preservation; content exclusion and whole-block character-budget packing; nDCG@5/@6, MRR@5, Success@5, rendered relevant content, conditional candidate hit rate, and optional pooled recall. End-to-end policies use a common ideal candidate universe, including baseline-only passages. Duplicate candidate positions remain intact.
- Evaluation runs one configuration in a fresh spawned process, with one warmup and three replay passes. It records load/first-inference/warm timings, Linux peak RSS, CPU allocation, dependency versions, model file checksums/storage, token distributions and truncation. Paired intervals resample issue groups with seed 0 and 1,000 draws. Selection is development-only; heldout evaluation requires frozen configurations and complete approved ceilings.
- `test_reranker.py` and `test_reranker_evaluation.py`: deterministic offline boundary and behavioral regressions, including real tokenization without model weights.

The production graph, prompt formatter, IssueState, shared requirements, Dockerfiles, environment settings, MCP interface, BGE embeddings, Qdrant schema and Redis memory are unchanged. The prospective reranked prompt order is simulated **only in the experiment**, with the dense path checked against the real formatter. No production worker or runtime feature flag was added: the plan makes those changes conditional on evaluation evidence.

## Observed verification

| Check | Observed result |
|---|---|
| Existing `.venv/bin/python test_graph_smoke.py` | 502 checks passed on Python 3.11.2 |
| New scoring + evaluation suites | 19 tests passed on Python 3.12.15 |
| Actual `compare` CLI, two synthetic result files | JSON and adjacent Markdown generated; no-activation decision; permissions 0600 |
| Existing-output and differing-fixture CLI guards | Nonzero exits; existing output unchanged; incompatible comparison not written |
| Actual `smoke` CLI with absent model | Nonzero exit with `local model directory is missing` |
| Python 3.12 execution isolation | Existing image, `--network none`, read-only root, temporary `/tmp`, one CPU, 1 GiB memory; container removed after exit |

Synthetic records exercise the software; they are **not Nesti relevance judgments or model benchmarks**. The network-isolated CLI run did not load a real reranker. ONNX Runtime emitted a read-only telemetry-ID warning during test imports and used an in-memory identifier; the tests passed.

## Missing evidence and dependency security

The operator explicitly chose **no model downloads**. No model or experiment dependencies were installed, and no production service was restarted. There were no local model artifacts or `.private/reranker/` query/judgment fixtures. The running production poller was left alone; no live capture or private issue export occurred.

The plan's Sentence Transformers 5.4.1 is upstream provenance, not a safe validated deployment pin. Its [PyPI advisory](https://pypi.org/pypi/sentence-transformers/5.4.1/json) reports [CVE-2026-68770](https://osv.dev/vulnerability/GHSA-jhr6-gm9c-rqjv): a local-directory trust-control bypass, fixed in 5.6.0. Scoring explicitly rejects versions below 5.6.0; it does not silently upgrade or substitute a model/backend. The complete CrossEncoder forward API was checked against the [5.6.0 source](https://github.com/huggingface/sentence-transformers/blob/v5.6.0/sentence_transformers/cross_encoder/model.py), not executed with real weights.

`experiments/requirements-reranker.txt` is intentionally **not frozen or created**. The plan requires Python 3.12 CPU compatibility, complete modular loading and real inference before freezing resolved dependencies. Neither that validation nor a safe-version lock can be claimed without the authorized prepared environment. Start subsequent compatibility work from CPU PyTorch 2.7.0, Transformers 5.7.0 and a security-fixed Sentence Transformers version, then freeze the actually successful resolved environment; the provenance CUDA specification must not be copied into CPU requirements.

There are no measured Nesti quality gains, real-model latency/RSS results, image-size results, actual live end-to-end latencies, retry/success improvements, billing savings or energy savings. Approved resource ceilings and separately authorized canary evidence are also absent. Consequently, this is not a completed model-selection benchmark and conditional production integration must not begin.

## Input and artifact contracts

Keep non-public data under `.private/reranker/`. Remove credentials and confidential identifiers before capture. No tool sanitizes real issue text on the operator's behalf.

Query JSONL rows require `query_id`, anonymized `issue_key`, `phase` (`plan`/`code`), `subject`, `description`, `plan`, `scope`, `attempt`, `detected_stack`, and `split` (`development`/`heldout`). Attempts are **one-based**; when recording pre-code IssueState, use its `attempt + 1`. Related plan/code/retry records must share one issue group and split. `slices` is an optional list of tags; coverage reports expect `api`, `migrations`, `primevue`, `tests`, `documentation`, `long-input`, and `terminology-collision`.

Capture requires `QUERIES_PATH.manifest.json` containing actual operator attestations:

```json
{"poller_stopped": true, "sanitized": true}
```

These attestations do not stop or inspect another poller. Stop it through the approved operational procedure before setting the field. Capture checks collection/embedder readiness, uses cached-only BGE loading, compares the complete registry document hashes with indexed hashes, and checks corpus evidence again afterward. It makes two searches per record, at limits eight and twenty, with the actual phase/scope/attempt query policy. Planning scope is classified before retrieval; code scope is taken from the recorded state.

Capture writes `OUTPUT_PATH` and `OUTPUT_PATH.manifest.json`. Rows preserve full candidate text and dictionaries, catalog documents/rendered content, exact query/filter, separate baseline/expanded retrieval durations, and empty `judgments`. Label keys are SHA-256 of compact UTF-8 JSON `[doc_path, heading, text]`, exposed by `candidate_key`; labels are integer 0/1/2. Identical content keys share a judgment but keep their positions. Missing labels are errors, not zeros. Empty captures remain `retrieval_unverified`; evaluation additionally requires a nonblank `independent_empty_evidence` explanation before using them.

The companion manifest stores capture time, query/snapshot/registry/corpus hashes, document-memory status, dependency/hardware evidence and model revisions. Adding labels changes the fixture bytes intentionally; evaluation hashes the finalized labeled bytes plus the unchanged manifest and split/candidates for comparisons. An optional `judged_universe` mapping must extend beyond retrieved candidates and include consistent candidate labels plus a `judged_universe_description`; otherwise corpus recall is explicitly not measured.

Each prepared model directory requires `reranker-artifact.json` with its exact `model_id` and `revision`, complete tokenizer/configuration/safetensors files, and, for Ettin, the complete saved pooling/dense/layer-normalization head. `MODEL_REVISIONS` contains the three plan-pinned revisions. This is an operator-prepared provenance declaration, not cryptographic proof of upstream authenticity; prepare artifacts from the trusted pinned source. Evaluation records actual local file hashes.

## Commands after prerequisites are supplied

Run in a separately prepared Python 3.12 environment with existing project dependencies and the compatibility-validated CPU dependencies. Every output path must be new.

```bash
python experiments/reranker_poc.py capture \
  --queries .private/reranker/queries.jsonl \
  --output .private/reranker/frozen.jsonl

python experiments/reranker_poc.py smoke \
  --model-dir .private/reranker/models/ettin-150m \
  --model-id cross-encoder/ettin-reranker-150m-v1 \
  --revision 025501c4e0f9bbeb4c5b198318e0089ff061cc14

python experiments/reranker_poc.py evaluate \
  --fixture .private/reranker/frozen.jsonl \
  --model-dir .private/reranker/models/ettin-150m \
  --model-id cross-encoder/ettin-reranker-150m-v1 \
  --revision 025501c4e0f9bbeb4c5b198318e0089ff061cc14 \
  --batch-size 4 --max-length 1024 --threads 1 \
  --output .private/reranker/ettin-150m-b4-l1024-t1.json

python experiments/reranker_poc.py compare \
  --results .private/reranker/ettin-150m-b4-l1024-t1.json \
  --output .private/reranker/development-comparison.json
```

Use 30–50 real development issue groups and at least 100 heldout labeled queries. Run configurations sequentially: Ettin batch sizes 2/4/8, lengths 512/1024/2048, and threads 1/2/4 within CPU allocation; MiniLM only at length 512. Pass all compatible result paths to `compare`; repeated passes are latency observations, not extra quality examples.

Before heldout inspection, the fixture manifest must contain `resource_ceilings` with nonblank `approval_evidence` and positive finite values for `warm_end_to_end_p95_seconds`, `cold_load_seconds`, `per_request_deadline_seconds`, `peak_rss_bytes`, and `allowed_concurrent_load`. Values must be operator-approved for the target deployment, not copied from synthetic tests. `compare` emits resource-eligible `development_selection` entries keyed by model ID, with revision/batch_size/max_length/threads. Freeze these in the manifest with `selection_frozen_at`; then run each frozen configuration once against heldout. Separate CLI invocations cannot prove an operator has never inspected heldout previously.

Timing labeled `estimated_end_to_end_seconds` is recorded capture retrieval duration plus replay scoring/selection/formatting, **not a measured live deployment SLA**. Deployment concurrency/headroom and actual end-to-end measurements remain independent promotion prerequisites. The comparison report can identify a conditional quality preference but always leaves activation unapproved at this standalone stage.

No deployment profile, production deadline or RAM SLA is invented. Production worker timeout/termination/fallback tests, graph-to-prompt integration, complete real-model offline execution and authorized canary observations remain conditional. Worker isolation, when implemented, cannot guarantee recovery from orchestrator/host SIGKILL or whole-host OOM.
