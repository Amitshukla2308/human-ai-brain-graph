# Development plan — OmniGraph next build

_Written 2026-04-24. Based on code read of `src/qwen_pipeline.py` (548 lines), `src/phase4_scale.py` (324 lines), `src/stage2_aggregate.py` (227 lines), `src/extractor.py` (180 lines, deprecated), and structure of `~/projects/hyperretrieval/`. Concrete file + line references throughout. Reliability + simplicity as evaluation axis for every phase._

## Starting state (what exists today)

**OmniGraph side (`~/projects/omnigraph/`):**

| File | Lines | Role | Status |
|---|---:|---|---|
| `src/qwen_pipeline.py` | 548 | 7-phase Qwen extractor. Key: `run_session()` at L364, `run_one()` at L494, `run_all()` at L515. Writes to `pilot/qwen/<prov>/<sid>.json`. | ✅ working, 3 pivots applied |
| `src/phase4_scale.py` | 324 | Per-provider normalizers (`normalize_claude_desktop/code/gemini/cline/antigravity`), `main()` driver. Writes normalized JSON to `pilot/normalized_full/<prov>/`. | ✅ working |
| `src/stage2_aggregate.py` | 227 | Reads all `<indir>/*/*.json`, emits `global_profile.json`. Single `aggregate(indir)` function. | ✅ working |
| `src/extractor.py` | 180 | Original POC, deprecated. Uses flat v0.1 schema. Kept for reference. | ⚠️ delete eventually |
| `docs/SCHEMA.md` | — | v0.2.1 locked schema. | ✅ canonical |
| `pilot/qwen/` + `pilot/full/` | — | 248 extracted sessions across 5 providers. | ✅ data |

**Key architectural facts surfaced from code read:**
- `qwen_pipeline.py:39-40`: `NORM_DIR = PILOT / "normalized"`, `OUT_DIR = PILOT / "qwen"` — hardcoded paths. Phase 4 scale.py symlinks into `pilot/normalized/` to trick the pipeline. Brittle.
- `qwen_pipeline.py:364 run_session()`: reads normalized JSON, runs 7 phases, writes full extraction. No incremental support. No skip-existing check.
- `phase4_scale.py:198 already_done()`: exists but only checked in scaler, not in pipeline itself. Resumability lives in the scaler layer.
- `stage2_aggregate.py:18 aggregate(indir)`: reads ALL files on every run. No incremental update. For 10K sessions this becomes unworkable.

**HyperRetrieval side (`~/projects/hyperretrieval/`):**

Numbered-pipeline build system in `build/`:
- `00_export_git_history.py` — git log → JSONL
- `01_extract.py` — file-level extraction
- `02_build_graph.py` — graph construction
- `03_embed.py` — vector embeddings
- `04_summarize.py` — per-node summaries
- `05_package.py` — bundle for serving
- `06_build_cochange.py` / `06b_build_cross_cochange.py` — co-change signals
- `08_build_ownership.py`, `08_generate_arch_docs.py`
- `09_build_granger.py` (and variants) — temporal causality
- `10_build_communities.py` / `10_build_criticality.py` — clusters + node importance
- `11_generate_guardrails.py`
- `12_targeted_summarize.py`
- `serve/` — HTTP + MCP exposure

Mapping for OmniGraph adoption: **git commits → sessions; files → Vault entity pages; co-change → co-mention; authors → session IDs**. Most of `build/` works if we produce a Vault-root that resembles a git repo with numbered-commit history.

## Source-of-data decision (from the decision tree above)

**Atelier PTY = primary source for all future work. Multi-provider scrapers = historical cold-start + cross-tool fallback.**

The extractor doesn't care where the canonical Turn[] comes from. What changes: we need an adapter interface rather than `phase4_scale.py`'s monolithic normalizer set.

## Phases ordered by dependency

### Phase 0 — Slug canonicalization + alias table

**Blocker for Phases 2, 3, 5** (Vault materialization, incremental aggregator, HyperRetrieval index). Currently Qwen produces clean slugs but there's no canonical registry to collapse near-duplicates (`zeroclaw` vs `zeroclaw-mcp` vs `zeroclaw-bridge`).

**Files added:**
- `src/canonical_slugs.py` (~150 lines): provides `canonicalize(mention_events) → mention_events` with a persistent alias table. Rules:
  - Lowercase + strip version suffixes (`-v2`, `-v6.2`)
  - Strip filler words (`the`, `mcp`, `-bridge`, `-core`)
  - Fuzzy-merge candidates with Levenshtein ≤2 if they share ≥1 co_mentioned target
  - Manual overrides via `pilot/slug_aliases.yaml`
- `pilot/slug_aliases.yaml` (small seed file, human-editable): 
  ```yaml
  # canonical → aliases
  zeroclaw: [zeroclaw-mcp, zeroclaw-bridge, zeroclaw-core]
  atelier: [atelier-phase-a, atelier-backend]
  ```

**Files changed:**
- `src/qwen_pipeline.py:364 run_session()` — add canonicalization pass after Phase 3 critique, before writing output. ~5 lines.
- `src/stage2_aggregate.py:18 aggregate()` — canonicalize mention events before building target_events dict. ~3 lines.

**Reliability + simplicity lens:**
- ✅ Simplicity: one module, one responsibility. Deterministic. No LLM dependency.
- ✅ Reliability: alias table is human-editable yaml; when automatic merge is wrong, human adds an override.
- ✅ Reversible: canonicalization is applied in-place at read-time; original `mentioned_as` preserved in each MentionEvent for audit.

**Effort:** 1 day.

---

### Phase 1 — Atelier PTY source adapter + decoupled normalizer interface

**What changes:** the source-specific normalizers in `phase4_scale.py:34-172` get restructured into a pluggable adapter pattern. Atelier PTY becomes a new adapter that bypasses most of the normalization path (the data is already structured).

**Files added:**
- `src/sources/__init__.py` — adapter registry
- `src/sources/base.py` (~50 lines): abstract `SourceAdapter` class with `iter_sessions() → Iterator[NormalizedSession]` + `session_id(raw) → str` + `is_session_stale(sid) → bool` (for incremental runs).
- `src/sources/atelier_pty.py` (~100 lines): reads Atelier's PTY session files (TBD Atelier-side path) + parses its structured event log into canonical Turn[]. Skips the heuristic content-flattening needed for multi-provider; Atelier already emits structured turns.
- `src/sources/claude_code.py` (~80 lines): lifted from `phase4_scale.py:73-92 normalize_claude_code()`.
- `src/sources/claude_desktop.py` (~80 lines): lifted from `phase4_scale.py:52-71 normalize_claude_desktop()`.
- `src/sources/gemini.py` (~80 lines): lifted from `phase4_scale.py:94-130 normalize_gemini()`.
- `src/sources/cline.py` (~80 lines): lifted from `phase4_scale.py:132-161 normalize_cline()`.
- `src/sources/antigravity.py` (~60 lines): lifted from `phase4_scale.py:163-172 normalize_antigravity()`.

**Files changed:**
- `src/phase4_scale.py:174-192 list_sessions()` — rewritten as 3 lines that defers to the adapter registry.
- `src/phase4_scale.py:229 main()` — take `--source <name>` flag; default enumerates all adapters.

**Files deleted:**
- `src/extractor.py` (180 lines) — deprecated POC. Remove.

**Reliability + simplicity lens:**
- ✅ Simplicity: adding a new source = adding one file. No scatter-and-gather.
- ✅ Simplicity: Atelier PTY adapter stays thin — just a format-translator, not a content-extractor.
- ✅ Reliability: each adapter is independently testable. Contract is explicit (the base class).
- ⚠️ Risk: the Atelier PTY format is TBD (depends on Atelier Phase A/B data layout). Build against a stub until Atelier exposes its session format. Document the contract in `atelier_pty.py`'s docstring so Atelier-side work can target it.

**Effort:** 1 day for refactor + stub; the Atelier-PTY real adapter is a half-day once Atelier's format is stable.

---

### Phase 2 — Event stream materialization + per-entity Vault

**What changes:** the aggregator currently works in-memory at query time. Phase 2 materializes two persistent artifacts derived from the extracted sessions.

**Files added:**
- `src/build_events_stream.py` (~80 lines): reads all `pilot/qwen/<prov>/<sid>.json` (or equivalent target location), writes `pilot/events/<YYYY-MM>.jsonl` (one file per month, append-only, timestamp-sorted). Also emits `pilot/events/index.json` mapping `target_id → [(timestamp, file_offset)]` for fast scan-by-target.
- `src/build_vault.py` (~150 lines): reads event stream + canonical slugs, produces `pilot/vault/<canonical_target_id>.md` — one Markdown file per entity, Obsidian-style backlinks to sessions (`[[session_<sid>]]`), co-mention edges (`see also: [[other-target]]`), chronological mention log at bottom.

**Vault file format** (per-entity, auto-generated):
```markdown
---
target_id: zeroclaw
target_type: Project
aliases: [zeroclaw-mcp, zeroclaw-bridge]
first_seen: 2026-02-28T21:06:00Z
last_seen: 2026-04-24T06:15:00Z
mention_count: 47
co_mentioned_top: [atelier, mcp-tools, rust]
status: active  # derived from last_seen, mention cadence
---

# zeroclaw

## Summary
Rust agent framework; MCP server exposing shell / file_read / file_write / cron_list / alex_status tools.

## Load-bearing decisions
- [[session_1772313542458]] — MCP tool set locked to 5 tools (shell, file_read, ...)

## Concerns raised against this target
- [[session_1772313542458]] — rmcp ^0.4 feature 'stdio' not found (build_error)

## Mention log
- 2026-04-24 — [[session_agent-a349a5d3707efa950]] reference (reader)
- 2026-04-23 — [[session_1772492573617]] first_introduction (writer)
- ...
```

**Files changed:**
- `src/qwen_pipeline.py:364 run_session()` — after writing extraction, trigger `build_events_stream.append_session()` and `build_vault.upsert_entities_from_session()`. ~10 lines.

**Reliability + simplicity lens:**
- ✅ Simplicity: Vault is derived. If corrupted, rebuild from extracted JSONs.
- ✅ Simplicity: one file per entity. Git-friendly. Human-readable. Obsidian-compatible out of the box.
- ✅ Reliability: event stream is append-only. Rebuild is just re-iterating extracted JSONs in timestamp order.
- ⚠️ Concern: per-entity file updates from each session = many small file writes. At 10K sessions scale, this is still fine (Markdown is cheap to write), but should batch-update within a session's extraction.

**Effort:** 2 days.

---

### Phase 3 — Incremental aggregator

**What changes:** `stage2_aggregate.py` currently re-reads everything. For 10K+ sessions this becomes the bottleneck. Replace with incremental update: each new session's extraction appends to stream + updates derived aggregates.

**Files changed:**
- `src/stage2_aggregate.py:18 aggregate()` — refactored to:
  - `aggregate_full(indir)` — old behavior, full rebuild. Kept for validation / disaster recovery.
  - `aggregate_incremental(indir, last_session_id)` — new. Reads only sessions past `last_session_id`, updates maintained `global_profile.json` in-place.
- `src/stage2_aggregate.py:216 if __name__` — CLI: `stage2_aggregate.py --incremental` (default) / `--full` (rebuild).

**Files added:**
- `pilot/_aggregate_state.json` — persistent cursor (last processed `session_id` + timestamp + checksum of aggregates). Enables resumable incremental runs.

**Reliability + simplicity lens:**
- ✅ Simplicity: incremental is additive. Full-rebuild still works as fallback.
- ✅ Reliability: checksum in aggregate_state allows detection of corruption; invalidation triggers full rebuild.
- ⚠️ Risk: Stage-2 inference patterns (P1 convergence, P5 concern lifecycle) have non-trivial window semantics. Incremental update of these requires careful reasoning — getting it wrong means stale inferences. Alternative: update `global_profile.json` fully on every N=10 sessions (batched), skip the window complexity.

**Effort:** 3 days (the window-semantics work is the real cost).

---

### Phase 4 — Projector / compiler (light-IR + Markdown targets)

**What changes:** new module that reads `global_profile.json` + Vault + events, emits target-specific compiled output (CLAUDE.md, light-IR for system prompts, Cursor rules, etc.).

**Files added:**
- `src/compiler/__init__.py` — registry of compile targets
- `src/compiler/base.py` (~40 lines) — abstract `ProjectionCompiler` with `compile(state: VaultState, max_tokens: int) → str`.
- `src/compiler/light_ir.py` (~150 lines) — per `05_LIGHT_IR_OUTPUT_FORMAT.md`. XML-tagged compact form.
- `src/compiler/claude_md.py` (~80 lines) — Markdown with YAML frontmatter, for CLAUDE.md / AGENTS.md consumers.
- `src/compiler/boot_context.py` (~100 lines) — JSON for Atelier Product Placement Flow consumption.
- `src/compiler/cursor_rules.py` (~60 lines) — Cursor-flavored rules.
- `src/compiler/gemini_md.py` (~40 lines) — Gemini's `GEMINI_SYSTEM_MD` env-var consumable format.
- `src/compile_cli.py` (~80 lines) — `omnigraph compile --target <name> --max-tokens N --out <path>` entry.

**Reliability + simplicity lens:**
- ✅ Simplicity: each compiler target is isolated. Deterministic text templating (Jinja2). No LLM in the compile path.
- ✅ Reliability: all compilers read the same `VaultState` (loaded once). If target compilation fails, other targets are unaffected.
- ✅ Simplicity: user can run `omnigraph compile --target claude_md --out ~/.claude/memory/user_profile.md` and pipe that wherever needed.

**Effort:** 2 days for first two targets (light_ir + claude_md); other targets are 0.5 days each and can ship incrementally.

---

### Phase 5a — HyperRetrieval integration (data backend only)

**What changes:** OmniGraph's Vault + events become a feed into HyperRetrieval's pipeline. HR's existing `build/` scripts are reused against an OmniGraph-shaped input. HR runs **headless** — no HR UI surfaced to the user. It produces graph / co-change / communities / criticality / granger signals that feed Phase 5b's viz and Phase 6's `omnigraph query`.

**Files added:**
- `src/hr_adapter/__init__.py`
- `src/hr_adapter/export_for_hr.py` (~120 lines): transforms OmniGraph artifacts into the shape HyperRetrieval's `build/01_extract.py` expects:
  - Vault markdown files → "source files"
  - MentionEvent stream → "commit history"
  - Canonical slug → "file path"
  - Session timestamps → "commit timestamps"
  - `co_mentioned_with` edges → "changed in same commit" signal
- `src/hr_adapter/bridge_cli.py` (~60 lines): `omnigraph index --full` runs HR's `build/00` through `build/12` over OmniGraph's artifacts.

**Files referenced (in HyperRetrieval, not modified):**
- `~/projects/hyperretrieval/build/01_extract.py` — takes our exported format as input
- `~/projects/hyperretrieval/build/02_build_graph.py` — graph over Vault nodes
- `~/projects/hyperretrieval/build/03_embed.py` — embeddings of Vault text
- `~/projects/hyperretrieval/build/06_build_cochange.py` — co-mention signals (reused as-is)
- `~/projects/hyperretrieval/build/09_build_granger.py` — temporal causality
- `~/projects/hyperretrieval/build/10_build_communities.py` — clusters
- `~/projects/hyperretrieval/build/10_build_criticality.py` — node importance
- `~/projects/hyperretrieval/serve/` — exposes the index via MCP + HTTP (consumed only by `omnigraph query`, not user-facing UI)

**Reliability + simplicity lens:**
- ✅ Simplicity: reuse, don't rebuild. Write an exporter, not a new retrieval layer.
- ✅ Reliability: if HR index corrupts, rebuild from OmniGraph artifacts. OmniGraph is the source of truth.
- ⚠️ Risk: HR is code-calibrated. Narrative markdown with [[wikilinks]] may need tuning. Validate on 50-session subset before committing to full-corpus index.
- ⚠️ Risk: HR's embedding model + chunking assumptions were designed for code. Prose embeddings may need a different model (e.g., `nomic-embed-text` or `bge-base-en`). Check and adjust.

**Effort:** 2 days for exporter + integration; additional 1 day for validation on narrative content.

---

### Phase 5b — Brain viz (custom frontend, not HR's chainlit)

**What changes:** anatomical wireframe brain rendering of the founder↔AI cognitive system with all 10 diagnostic hypotheses as overlay modes. Per `07_BRAIN_VIZ.md`. Frontend built in **Claude Design** (desktop app) + **Claude Artifacts** (React), served from a tiny FastAPI backend reading Phase 5a's outputs.

**Files added (backend):**
- `src/viz/__init__.py`
- `src/viz/hypotheses.py` (~400 lines): 10 pure functions (one per hypothesis). Each reads Vault + events + HR-exported signals, returns `{firing_pattern, verdict, top_evidence}`.
- `src/viz/build_brain_state.py` (~120 lines): assembles `pilot/viz/brain_state.json` — the single JSON contract the frontend consumes. Schema in `07_BRAIN_VIZ.md`.
- `src/viz/sanitize.py` (~100 lines): three levels (None / Named-entities-stripped / Aggregated-only). Applied client-requested at export time.
- `src/viz/serve.py` (~80 lines): FastAPI on `localhost:8787`. `GET /brain/state`, `POST /brain/export {level}`. That's it — 2 endpoints, the only wire surface the frontend sees.

**Frontend is Atelier-side, not OmniGraph-side.** Per the layering declaration, the brain viz UI lives in `~/atelier/`. A draft scaffold (Vite + React + R3F, particle cloud, fibers, hypothesis sidebar, verdict card, timeline, export dialog) was written 2026-04-24 and parked at `~/atelier/apps/brain-viz-draft/` — see its README for status and integration notes. OmniGraph's 5b commitment is the JSON contract + backend endpoints; rendering is not this repo's responsibility.

**Reliability + simplicity lens:**
- ✅ Simplicity: one JSON contract (`brain_state.json`). Frontend and backend agree on nothing else.
- ✅ Simplicity: only 2 wire points total (`/brain/state` GET and `/brain/export` POST). Claude Design iteration doesn't touch them.
- ✅ Reliability: hypothesis functions are pure + deterministic. No LLM in the render path.
- ⚠️ Evidence threshold: below N=10 data points, a hypothesis must render as "insufficient data" — a false verdict is worse than no verdict.
- ⚠️ Design iteration cycle is separate from integration cycle. Keep the stub `MOCK_BRAIN_STATE` identical in shape to production `brain_state.json` — if the contract drifts, Claude-Design-generated components break at wire time.

**Effort:** 2 days backend (hypothesis engine + state builder + FastAPI + sanitize). 3-5 days frontend (Claude Design iteration + 5 Artifact components + Vite wire-up). Total: **5-7 days for 5b.** Can run in parallel with 5a after the JSON contract is frozen.

---

### Phase 6 — `omnigraph` CLI (ingest, watch, import, compile, index, query)

**What changes:** unify the scattered entry points into a single command-line tool.

**Files added:**
- `src/cli/__init__.py` — click/typer-based CLI dispatch
- `src/cli/ingest.py` (~150 lines) — auto-detect installed providers' dump paths per platform (macOS / Linux / WSL / Windows), copy dumps to canonical location with user consent.
- `src/cli/watch.py` (~100 lines) — periodic polling daemon. Watches known dirs + re-runs extract+aggregate+compile pipeline incrementally.
- `src/cli/import_cmd.py` (~80 lines) — handles user-dropped files in `~/.omnigraph/drop/`. Auto-detects format (JSON, JSONL, markdown, conversation export).
- `src/cli/compile_cmd.py` (~40 lines) — wraps Phase 4 compilers.
- `src/cli/index_cmd.py` (~40 lines) — wraps Phase 5 HR integration.
- `src/cli/query_cmd.py` (~80 lines) — `omnigraph query "what drifts have I had with MCP tools?"` — routes through HR's serve interface.

**Platform-specific provider paths** (encoded as constants in `src/cli/ingest.py`):
```python
PROVIDER_PATHS = {
    "claude_code": {
        "linux": ["~/.claude/projects", "~/.claude/history.jsonl"],
        "wsl":   ["~/.claude/projects", "/mnt/c/Users/*/AppData/Roaming/Claude/claude-code"],
        "mac":   ["~/.claude/projects", "~/Library/Application Support/Claude"],
        "win":   ["~/AppData/Roaming/Claude/claude-code"],
    },
    "claude_desktop": {
        "wsl": ["/mnt/c/Users/*/AppData/Roaming/Claude/local-agent-mode-sessions"],
        # ...
    },
    "gemini_cli": { ... },
    "cline": { ... },
    "antigravity": {
        "wsl": ["/mnt/c/Users/*/.gemini/antigravity"],
        # .pb decryption deferred — read from .data/ siblings only
    },
}
```

**Reliability + simplicity lens:**
- ✅ Simplicity: one binary, Unix-subcommand style. `omnigraph --help` is the entry point.
- ✅ Reliability: each subcommand is idempotent. Running `omnigraph ingest` twice doesn't duplicate.
- ⚠️ Risk: provider paths break on tool updates. Keep this file small and separate so patches are quick to ship.
- ✅ Privacy: no data leaves local machine by default. Cloud sync is explicit opt-in, separate command (not shipped in v1).

**Effort:** 3 days for ingest + watch + import; 1 day each for compile/index/query subcommands (they're wrappers).

---

### Phase 7 — Atelier Product Placement Flow consuming OmniGraph

Out of scope for this plan (Atelier-side work). Noted as dependency. Atelier-side needs:
- Calls `omnigraph compile --target boot_context --out ./project_boot.json` at project-boot time.
- Renders the 6-phase PPF from `project_boot.json` content as interactive cards (per `04_PROPOSED_BUILD_ORDER.md` Step 3).
- Produces a project charter → writes back to `omnigraph` as a first-party entity (`pilot/vault/<project>.md`).

Detailed Atelier plan lives in Atelier's own planning docs; this plan commits OmniGraph to exposing the `boot_context` compile target (Phase 4 above) as the integration surface.

---

## Cross-cutting concerns

### Schema evolution
v0.2.1 is locked for pilot. v0.3 (deferred) will likely include:
- `co_mentioned_with` dedup at scale (per `03_APPLICATIONS.md` notes)
- `has_reflection_markers: bool` in session_meta
- `reliability_weight: float` per provider in session_meta (for Stage-2 skew correction)

These are future. Current plan builds on v0.2.1 as-is.

### Testing
- `src/sources/` each adapter gets a unit test with a fixture session.
- `src/compiler/` each target gets a golden-file test (compile → diff against known-good output).
- `src/canonical_slugs.py` test table of known alias merges.
- End-to-end: one-session run through ingest → extract → aggregate → compile on a tiny corpus.

Not in scope for this plan: Atelier's side tests, HR's internal tests.

### Documentation updates
- `README.md` at OmniGraph root — explain layering ("Atelier — powered by OmniGraph"), entry points, CLI.
- `docs/SCHEMA.md` — no change (v0.2.1 locked).
- New: `docs/ARCHITECTURE.md` — the pipeline diagram from `03_APPLICATIONS.md` §Architecture for scale.
- New: `docs/CLI.md` — reference for `omnigraph` commands.

### Deprecations
- `src/extractor.py` — delete (was v0.1 POC, fully superseded).
- `src/qwen_pipeline.pre_v2_pivots.py` — keep for now as rollback reference; delete after v0.3 ships.
- `src/ir_vs_prose_bench.py` — move to `research/` directory (archival).
- `pilot/_opus_batch_4_extract.py` — appears to be an orphan from the agent misfire; inspect + delete.

## Build order summary

| Phase | Days | Blocker for | Files changed | Files added |
|---|---:|---|---|---|
| 0. Canonical slugs | 1 | 2, 3, 5 | 2 existing | 2 new |
| 1. Source adapters + Atelier PTY stub | 1 | Atelier-PTY integration | 2 | 6-7 |
| 2. Event stream + Vault | 2 | 3, 5 | 1 | 2 |
| 3. Incremental aggregator | 3 | scale | 1 | 1 |
| 4. Compiler / projector | 2 + | 7 | 0 | 7-8 |
| 5a. HyperRetrieval integration (data) | 2-3 | 5b, query features | 0 | 2-3 |
| 5b. Brain viz (frontend + backend) | 5-7 | shareable surface | 0 | 10-12 |
| 6. `omnigraph` CLI | 4-5 | user adoption | 0 | 7-8 |
| 7. Atelier PPF consumer | — | (Atelier-side, not counted) | — | — |

**Total: ~20-25 days of focused work** (5b adds the brain-viz surface). Atelier-side work (Phase 7 + harness gaps per `SESSION_02_HANDOFF.md` addendum) runs in parallel.

## Where I'd start

**Phase 0 today.** Canonical slugs + alias table is 1 day, unblocks three later phases, and can be applied retroactively to the 248 already-extracted sessions (re-run the Stage-2 aggregator with canonicalization and compare P6 cross-provider delta). That's both a real unlock and a validation that canonicalization works without schema change.

**Phase 1 next** because the Atelier-side integration depends on knowing the PTY-adapter shape. Writing the adapter stub makes the Atelier contract concrete, which lets Phase A/B development proceed without ambiguity on what Atelier has to produce.

Phases 2-6 can be paralleled or sequenced based on what Atelier needs first. If Atelier's Product Placement Flow is the demo target, **Phase 4 (compiler) + Phase 2 (Vault) are the shortest path** — skip incremental aggregator for now (Phase 3 is only needed past ~5K sessions), skip HR integration until retrieval speed becomes a bottleneck.

## Open questions

1. **Atelier PTY session format** — need Atelier to commit to a format before the real adapter can be finished. Stub ships with TODO.
2. **Slug-alias ownership** — human-editable yaml or in-product UI? v1: yaml. v2: expose alias-merge as part of Atelier's settings.
3. **HyperRetrieval dependency** — do we add as git submodule, Python-path sibling, or packaged? My lean: Python-path sibling for now (same workspace as `~/projects/hyperretrieval/`), package later.
4. **Schema versioning** — when v0.3 lands, do we migrate old extractions in-place or run both side-by-side? My lean: side-by-side with explicit migration CLI command.

## Success criteria (how we know each phase is done)

| Phase | Success condition |
|---|---|
| 0 | P6 cross-provider match count on current 248-session corpus increases by ≥2× after canonicalization vs current baseline. |
| 1 | Stub Atelier-PTY adapter can ingest a hand-crafted fixture session through the full extractor pipeline. |
| 2 | Vault renders a per-entity Markdown page for top-30 entities; each page has at least 1 backlink to a session; Obsidian can open the vault directory. |
| 3 | `aggregate_incremental` on +1 session takes ≤5% of the time `aggregate_full` takes on 248 sessions. |
| 4 | Compiling `claude_md` target produces file <800 tokens for current global_profile; light-IR target reproduces the benchmark format exactly; compile time <200ms for either. |
| 5 | `omnigraph query "drift patterns on MCP tools"` returns ≥3 relevant sessions from the 248-session corpus in <500ms. |
| 6 | Fresh OS install: `omnigraph ingest` → `omnigraph compile --target claude_md` → write to `~/.claude/CLAUDE.md` in under 10 minutes end-to-end on a corpus of ≤500 sessions. |

Each phase has a gating metric; don't move to the next until the prior is met.
