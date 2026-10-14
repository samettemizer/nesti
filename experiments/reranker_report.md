# PyTorch documentation reranker: implementation and decision

**Decision: not approved for activation.**

Reference: `.private/PLAN_NESTI_PYTORCH_DOCUMENTATION.md`, edition 3.0.
Branch: `feat/pytorch-documentation-reranker`.
Machine-readable verification: `experiments/reranker_report.json`.

## Oturum sonu kaydı — 14 Ekim 2026

Yarım kalan Nesti entegrasyonu tamamlandı; aşağıdaki test ve gerçek-model doğrulamaları geçti. Varsayılan kapalı (`NESTI_RERANKER_ENABLED=false`) birleştirme için bu oturumdaki doğrulamalarda engel saptanmadı. Bu karar canlı aktivasyon onayı değildir: gerçek issue kalite karşılaştırmaları, onaylı kaynak profili ve eşzamanlı yük ölçümleri hâlâ eksiktir. GitLab issue açılmadı, OpenRouter çağrısı yapılmadı ve çalışan servis yeniden başlatılmadı. Worker kapanışındaki semaphore temizleme uyarısı aşağıda kayıtlıdır; child sürecinin toplandığı doğrulandı.

Commit mesajı: `Complete default-off documentation reranker integration with bounded workers, offline model provisioning, and tokenizer overflow fixes.`

## Delivered scope

- `reranker.py`: lazily imported CPU/FP32/SDPA scoring through the complete Sentence Transformers CrossEncoder, plus a serialized spawned worker with bounded IPC/load/inference waits and termination/reaping. Failures latch the worker unavailable until process restart. Raw finite scores preserve input positions. Tokenizer encodings retain the first 96 and last 32 query tokens above 128; only the passage is then truncated to the pair budget. Discarded overflow windows are removed before merging/post-processing to prevent combinatorial allocation. Candidate dictionaries and stored text are not changed.
- `experiments/reranker_poc.py`: explicit-path `capture`, `evaluate`, `smoke`, and `compare` CLI commands. Capture is read-only; evaluation never queries Qdrant or calls an LLM. Models are local-only. Output artifacts are created with mode 0600 and existing files are never overwritten.
- `experiments/reranker_evaluation.py`: strict labeled-fixture validation; separate merged-lane/dense/neural ranking comparisons and legacy/expanded-dense/expanded-neural selection comparisons; six-slot lane preservation; content exclusion and whole-block character-budget packing; nDCG@5/@6, MRR@5, Success@5, rendered relevant content, conditional candidate hit rate, and optional pooled recall. End-to-end policies use a common ideal candidate universe, including baseline-only passages. Duplicate candidate positions remain intact.
- Evaluation runs one configuration in a fresh spawned process, with one warmup and three replay passes. It records load/first-inference/warm timings, Linux peak RSS, CPU allocation, dependency versions, model file checksums/storage, token distributions and truncation. Paired intervals resample issue groups with seed 0 and 1,000 draws. Selection is development-only; heldout evaluation requires frozen configurations and complete approved ceilings.
- `graph/nodes.py`: default-off integration retains the exact eight/six baseline, then expands to twenty only for a nonempty enabled request. Reranking replays the baseline PHP/Vue/practice slots; any expansion/scoring failure returns the entire untouched baseline.
- `prompt_builder.py`: complete, coherent rerank markers preserve supplied lane order; absent, partial, nonfinite or inconsistent markers retain legacy dense ordering. Catalog-content exclusions and whole-block character budgets are unchanged.
- `scripts/prepare_reranker.py`, `experiments/requirements-reranker.txt`, `Dockerfile`, `.env.example`: pinned CPU dependencies and controlled build-time preparation of complete licensed artifacts, with an optional operator-supplied profile. No profile or resource SLA is invented.
- `test_graph_smoke.py`, `test_reranker.py`, `test_reranker_evaluation.py`: offline graph, scoring, worker, evaluation and artifact-preparation regressions, including real tokenizer encodings without model weights.

IssueState, graph gates/cleanup routes, shared requirements, MCP image/interface, BGE embeddings, Qdrant schema and Redis memory are unchanged. MCP remains dense-only. The running deployment was not restarted or activated.

## Observed verification

| Check | Observed result |
|---|---|
| `python test_graph_smoke.py`, isolated Python 3.12.15 container | 554 checks passed |
| `python -m unittest test_reranker test_reranker_evaluation` | 44 tests passed, including bounded worker failure/reaping and artifact-preparation guards |
| New tokenizer overflow regression before correction | Failed: pair post-processing retained combinations of discarded windows |
| Real Ettin 150M CLI smoke, network disabled | Passed: Mars ranked above Venus/apples; finite raw scores; metadata unchanged; warm model reused |
| Real long-input smoke after correction | 608 query tokens → 128; 13,501 passage tokens → 381; complete pair 512 tokens |
| Real spawned worker → `_retrieve_chunks` → plan/code prompts | Passed: low-dense-score Mars replaced Venus, both prompts used Mars, warm request reused the same worker, child reaped |
| Missing-artifact graph fallback in the real-worker smoke | Untouched baseline dictionaries and byte-identical baseline prompts |
| `docker build -t nesti-orchestrator:reranker-validation .` | Passed, including `pip check` and real pinned-artifact/license preparation |
| Built image, no host source/model mounts, network disabled | All 554 graph checks, 44 unit tests and the real-model CLI smoke passed at one CPU / 2 GiB |

Initial real-model runs used the previously prepared local artifact and CPU virtualenv mounted read-only into the existing image. The subsequent full image build independently installed the pinned requirements and prepared the artifact at `/opt/nesti-reranker`; its offline checks required no host source/model mounts. All corrected real-model runs disabled networking and used one CPU / 2 GiB. They made no LLM calls and used synthetic frozen candidates, not live Qdrant. The temporary smoke profile was deleted; its deadlines were test limits, not deployment approval.

The first uncorrected long-input run exited 137 at 2 GiB. At 4 GiB it completed but spent 153.340 seconds preparing tokens. After removing discarded overflow windows, the same long-input token preparation took 0.057 seconds and the complete smoke passed at 2 GiB. These are individual diagnostic observations, not deployment percentiles or proof of memory headroom. The final baked-model worker smoke observed 6.302 seconds cold and 0.192 seconds warm for two candidates. It also emitted a multiprocessing semaphore cleanup warning after explicitly terminating the model worker; child reaping was verified. The ordinary suites emitted an ONNX Runtime read-only telemetry-ID warning and passed.

## Activation evidence still missing

The interrupted work had already prepared an Ettin 150M artifact and Python 3.12 CPU environment under `.private/reranker/`. Initial checks reused them; the full Docker build then exercised controlled downloads independently. The old report's “no local artifacts” and “no real inference” statements are superseded by the observed checks above.

The validated combination is PyTorch `2.7.0+cpu`, Sentence Transformers `5.6.0`, Transformers `5.7.0`, NumPy `2.5.3` and Tokenizers `0.22.2`. The observed dependency closure is pinned in `experiments/requirements-reranker.txt`, separate from shared/MCP dependencies. Sentence Transformers before 5.6.0 remains rejected because of [CVE-2026-68770](https://osv.dev/vulnerability/GHSA-jhr6-gm9c-rqjv). Compatibility smoke does not approve a deployment resource profile.

There are still no sanitized real query groups, relevance labels, frozen development/heldout comparisons against 68M/MiniLM, approved deployment resource ceilings, or measured co-located headroom. No live capture, GitLab issue, LLM canary, production restart or activation was performed. Nesti quality gains, retry reductions, billing savings and energy savings remain unmeasured. `NESTI_RERANKER_ENABLED=false` remains the default.

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

## Deployment and rollback

Build-time preparation downloads only pinned artifacts; runtime is offline and never downloads. The orchestrator image includes the default 150M artifact, not an assertion that 150M won the quality comparison. MCP does not install the CPU reranker requirements or prepare its artifact.

Reproduce the self-contained image check without activating the poller:

```bash
docker build -t nesti-orchestrator:reranker-validation .
docker run --rm --network none --read-only --tmpfs /tmp --cpus 1 --memory 2g \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python \
  nesti-orchestrator:reranker-validation experiments/reranker_poc.py smoke \
  --model-dir /opt/nesti-reranker \
  --model-id cross-encoder/ettin-reranker-150m-v1 \
  --revision 025501c4e0f9bbeb4c5b198318e0089ff061cc14
```

After the quality/resource gate passes, supply a non-secret approved profile from the Docker build context using `--build-arg NESTI_RERANKER_PROFILE=relative/path.json`. Its exact keys are `model_id`, `revision`, `batch_size`, `max_length`, `threads`, `load_timeout_seconds`, and `inference_timeout_seconds`. Its pinned identity selects the prepared model. The build context excludes `.private`; never copy issue text, labels or credentials into a deployment artifact. With no profile, an enabled attempt falls back to the baseline.

Set `NESTI_RERANKER_ENABLED=true` only for an approved deployment/canary, with `NESTI_RERANKER_MODEL_PATH=/opt/nesti-reranker`, and recreate the orchestrator service. Roll back by setting the flag false and recreating the service; editing `.env` alone does not update an existing container. No reindex is needed.

Worker isolation handles catchable failures and worker-only termination, not orchestrator/host SIGKILL or whole-host OOM. Keep the feature disabled until the independent quality and deployment-resource criteria above are satisfied.
