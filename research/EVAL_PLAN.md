# EVAL PLAN — Can Qwen3.6-35B-A3B replace Atelier's Drafter / Implementor?

**Status:** plan of record for a verifiable evals run. Not the eval itself — that's a build.
**Date:** overnight 2026-04-23 → 2026-04-24
**Question:** With OmniGraph in place providing meta-learnings + chronological patterns, can Qwen3.6-35B-A3B (local, 256K ctx, thinking mode) replace the Atelier **Drafter** role, **Implementor** role, or both?

## Reframe (v1.1) — the real question

**Original framing (v1.0):** "can Qwen match Sonnet on the same input?" This measures raw capability but is an unfair test. Smaller models need better-engineered inputs to reach the same output. OmniGraph's entire reason to exist is input engineering.

**Revised framing (v1.1):** the eval has two questions:
1. **Floor** (naked): how much worse is Qwen than Sonnet on identical input? (This tells you the raw capability gap — useful for context, not for product decisions.)
2. **Ceiling** (engineered): with OmniGraph + reasonable input scaffolding (templates, few-shot, decomposition, tool wrappers), does Qwen reach Sonnet-naked quality? (This is the product decision.)

Track C is now the load-bearing test — it measures whether OmniGraph closes the gap. Track E (new) diagnoses what input engineering is needed when Qwen fails.

## Headline verdict (pre-empirical, from benchmark synthesis)

| Role | Recommendation | Rationale |
|---|---|---|
| **Implementor** | ✅ **Viable with scaffolding.** Ship behind retry-wrapper + schema validator. | SWE-bench Verified 73.4 (vs Sonnet 4.6 @ 79.6 — 7pt gap but real coding capability). MCPMark 37.0 is best open-weight. Good field reports. |
| **Drafter** | ⚠️ **Marginal / risky.** Keep Sonnet 4.6 or Opus 4.7 here by default. | Persona+knowledge tradeoff (persona prompting degrades factual accuracy). 3B active param attention-to-detail ceiling. Drafter's Socratic+taste combination is exactly the failure regime. |
| **Both (full replace)** | ❌ **Not yet.** | No long-horizon benchmark. Canvas-node execution is unvalidated territory. |
| **Hybrid** | ✅ **Recommended path.** | Qwen as Implementor + Claude as Drafter. Route by task type. Qwen as local fallback Drafter with explicit quality gates for air-gapped use. |

**But:** this verdict is based on public benchmarks that don't measure the two capabilities Atelier + OmniGraph add: (1) meta-profile-conditioned generation, (2) Canvas-node-graph task execution. Those are **the empirical unknowns** the custom evals below must answer.

## Load-bearing evidence

### From Atelier role specs (Agent 1 report)

- **Drafter** capabilities: conversational planning, canvas node proposals, Socratic dialogue, plan.md authoring, reflection pass, stance/lens-selection, transparency. Cannot edit files / commit / build. Soul requires: terse, evidence-first, completion-driven (not novelty-driven), lens-select before evaluate, warm but not performative.
- **Implementor** capabilities: full tool suite (Read/Write/Edit/Bash/MCP), scoped to git worktree per task, budget-capped (50%/80%/100% checkpoints), works strictly from approved `plan.md`. Cannot invent scope, cannot skip Guardian scans (post-MVP), must verify reachability (end-to-end) not just local tests.
- **Context envelope (both):** own plan + parent plan + dependency plans only. Never whole project. Must respect stage-gated autonomy (full in pre-MVP, classification-gated post-MVP).
- **Critical v1 failure to avoid:** "coherence over correctness" — being rewarded for well-structured output vs actual user task completion.

### From Qwen3.6-35B-A3B public benchmarks (Agent 2 report)

| Benchmark | Qwen3.6 | Sonnet 4.6 | Opus 4.6/4.7 | Gap |
|---|---:|---:|---:|---|
| SWE-bench Verified | 73.4 | 79.6 | 80.8 | -6 to -7 pts |
| Terminal-Bench 2.0 | 51.5 | (not public) | (not public) | - |
| MCPMark | **37.0** | — | — | **best open-weight** |
| AIME 2026 | **92.7** | — | — | - |
| GPQA Diamond | 86.0 | ~84 | ~87 | parity |

**Known weaknesses** (sourced, Agent 2):
1. **Tool-call passivity / one-shot bias** — "almost never query a tool more than once, either accepting initial results or arguing a different choice is correct without validation" (HF community). Lethal for iterative Implementor loops.
2. **Sometimes refuses tool use and guesses instead** — breaks MCP schema reliability.
3. **3B active attention ceiling** — inconsistent adherence to multi-constraint system prompts.
4. **Persona-vs-knowledge tradeoff** — persona prompting degrades factual accuracy (PRISM research). Drafter is *exactly* this regime.
5. **No public long-horizon multi-step benchmark.**

**Strengths:** MCPMark 37%, 262K context + preserve_thinking, positive community reports on local coding agents.

## Evaluation design — 4 tracks, 15 tests

Each test is **verifiable** (pass/fail criterion is mechanical or rubric-scored by Claude Opus against fixed 5-axis rubric). Tests run as `eval/<track>/<test_id>.py` emitting `results.jsonl`. Single summary aggregator produces `eval/REPORT.md`.

### Track A — Implementor: code execution on real Atelier-shaped plan.md tasks

**Verification basis:** mechanical (tests pass / don't, acceptance criteria met / not, budget respected / not).

| ID | Task | Pass criterion |
|---|---|---|
| A1 | **Simple plan.md execution**: synthetic `plan.md` with Intent + Non-goals + Acceptance (3 failing tests), Qwen must make them pass without editing tests. | Tests green. Commit produced. Budget respected. |
| A2 | **Plan with dependency**: `plan-child.md` depends on `plan-parent.md` (shared interface). Qwen must load parent envelope, not mutate parent, and ship child consistently. | Child tests green. Parent tests still green. No parent files modified. |
| A3 | **Reachability verification**: task requires end-to-end curl check, not just local pass. | `curl http://localhost:PORT/endpoint` returns 2xx with expected body. |
| A4 | **Budget discipline**: `--max-budget-usd 2.00` ceiling. Qwen must checkpoint at 50%/80% and stop cleanly at 100%. | Self-report contains 50%/80% checkpoints. Total token spend ≤ budget×equiv rate. |
| A5 | **Revert-first on failing attempt**: inject a partial implementation that breaks existing tests. Plan says "finish this." Qwen must revert the broken state before writing new code. | Git log shows revert commit before new work. Final state tests green. |
| A6 | **Tool-retry instrumentation (key Qwen weakness)**: mock MCP tool that fails on first call with a recoverable error, succeeds on retry. | Qwen retries + succeeds. (Known Qwen failure mode: one-shot-then-rationalize). |

### Track B — Drafter: plan authoring + Socratic dialogue

**Verification basis:** rubric-scored (5-axis, Opus as judge, 1-5 each, pass ≥18/25).

Rubric axes:
- **Scope discipline**: did output decompose vague ask into 2-4 named nodes or propose exactly what was asked?
- **Tradeoff surfacing**: are alternatives + their drawbacks named?
- **Acceptance-criteria quality**: reachability included, not just local correctness?
- **Soul adherence**: terse, evidence-first, no fluff, lens-selected before judging?
- **Bounded autonomy**: does output respect "no filesystem edit" constraint and propose via canvas only?

| ID | Task | Pass criterion |
|---|---|---|
| B1 | **Vague ask decomposition**: founder says "improve the onboarding." Expected: 3-4 scoped canvas node proposals with non-goals. | Rubric ≥18/25. |
| B2 | **Plan.md authoring**: given a clear task, produce full plan.md (Intent/Non-goals/Acceptance/Deps/Children/Budget/Artifacts). | All 7 sections present + ≥18/25. |
| B3 | **Socratic pushback**: founder asserts a solution that's misaligned with prior decisions (fed via meta-profile). Drafter should surface the misalignment, not silently comply. | Pushback occurs + rubric ≥18/25. |
| B4 | **Checkpoint-and-park**: mid-plan, founder introduces a digression. Drafter must propose parking vs pivoting, not silently drop prior plan. | Explicit park proposed + rubric ≥18/25. |

### Track C — OmniGraph meta-profile ablation (the KEY question)

**Verification basis:** delta metrics between two runs.

For each test in Track A + B, run it **twice**:
- **Run X (naked):** Qwen + system prompt + task. No OmniGraph context.
- **Run Y (grounded):** Qwen + system prompt + task + injected meta-profile (selected entries from OmniGraph global_profile: user's confirmed mental moves + rules + latent concerns relevant to the task domain).

Compute delta per test:
- Track A: test pass rate Y - X; budget spend X - Y (lower is better with meta-profile).
- Track B: rubric score Y - X.

**Hypothesis:** grounded runs show ≥10% improvement on Track A pass rate and ≥2 point improvement on Track B rubric. If <5% improvement, OmniGraph injection provides marginal value for this use case — recalibrate.

### Track E — Input-engineering gap analysis (diagnostic, v1.1 addition)

**Purpose:** when Qwen fails a Track A/B/D test in the naked mode, progressively enrich the input until it passes or we exhaust the scaffolding options. Record which attempt unlocked success. The cost to reach Sonnet-naked quality IS the product answer.

**Progressive-enrichment protocol** — on every Qwen failure, retry with these attempts in order until pass:

| Attempt | Input augmentation |
|---|---|
| 1 | naked task (baseline — already captured in Mode 1) |
| 2 | + explicit schema / structured output template |
| 3 | + 3 few-shot exemplars (from journal or prior oracle output) |
| 4 | + task decomposition into explicit sub-goals |
| 5 | + OmniGraph meta-profile slice (pre-filtered relevant entries) |
| 6 | + step-by-step acceptance criteria with anchored examples |
| 7 | + retry-wrapper with schema validator feedback (tool-use scaffolding) |

**Record per test:**
- `first_passing_attempt` (1-7, or `failed` if none passed)
- `failure_class` (see taxonomy below)
- `tokens_added` (prompt-size delta from Attempt 1 to the winning attempt — a proxy for engineering cost)

#### Failure taxonomy (classify each Qwen miss)

1. **Schema adherence** — output wrong shape → fixable with structured template (Attempt 2)
2. **Decomposition** — can't hold multi-step → fixable with sub-goal breakdown (Attempt 4)
3. **Reasoning ceiling** — wrong conclusion even with right input → **capability hard-stop, NOT engineerable**
4. **Context-integration** — has the info but doesn't use it → fixable with anchored examples + forced-citation rubric (Attempt 3 or 6)
5. **Tool-use** — fails at MCP schema or doesn't retry → fixable with retry-wrapper (Attempt 7)

**Only class (3) is a hard no.** Everything else is an engineering-investment decision with bounded cost.

#### Decision rule post-E

- If **≥80% of failures fall in classes 1, 2, 4, 5** and most are fixable within Attempts 2-5 (systematizable in a prompt template) → **Qwen + OmniGraph + standard scaffolding is a viable Implementor/Drafter substitute.**
- If **>30% of failures are class 3 (reasoning ceiling)** → Qwen hits its capability wall on this task class; keep Claude.
- If fixable but requires per-task tuning (Attempts 6-7 consistently) → borderline; economic/latency tradeoff.

### Track C reframe — what it's really measuring

The original Track C compared Qwen-naked vs Qwen-grounded. Under v1.1 it becomes a three-way:

| Condition | What it measures |
|---|---|
| **Qwen-naked** | Raw Qwen capability floor |
| **Qwen-grounded (with OmniGraph)** | **Does OmniGraph close the gap?** ← product decision |
| **Sonnet-naked** | The target quality bar |
| *(optional)* Sonnet-grounded | Diminishing returns on the stronger model |

**Success condition:** Qwen-grounded ≥ Sonnet-naked on rubric / pass rate.

If Qwen-grounded < Sonnet-naked by >10%: OmniGraph alone isn't enough — Track E tells us what additional scaffolding gets us there.

### Track D — Canvas-node-graph execution (greenfield, most interesting)

**Verification basis:** graph-level metrics (dependency respect, artifact completeness, budget across graph).

| ID | Task | Pass criterion |
|---|---|---|
| D1 | **3-node linear chain**: N1 → N2 → N3. Qwen Implementor runs each sequentially. | All 3 tests green. Cross-node contracts respected. Total budget ≤ sum of per-node budgets. |
| D2 | **Diamond dependency**: N1 → {N2, N3} → N4. N4 depends on both N2 and N3 artifacts. | N4 tests green using BOTH N2 and N3 outputs. |
| D3 | **Drafter → Implementor handoff**: Drafter writes plan.md from vague ask (B1 output). Implementor executes it (A-track-shaped). End-to-end: vague ask → green tests. | End-to-end green. Handoff artifact quality rubric ≥18/25. |
| D4 | **5-node project**: small real-ish project (e.g., "build a CSV-to-JSON converter with CLI + tests + README"). Drafter proposes nodes, Implementor executes. | All acceptance criteria met. Reachability (CLI invocation) works. |

## Runner design

- `eval/run.py --model qwen --mode naked` — Track A, B, D runs against Qwen (LM Studio endpoint).
- `eval/run.py --model qwen --mode grounded` — same with OmniGraph injection.
- `eval/run.py --model claude-sonnet-4-6 --mode grounded` — reference run as ceiling.
- `eval/aggregate.py` — produces `REPORT.md` with per-track pass rates, rubric distributions, meta-profile delta table, side-by-side Qwen-vs-Sonnet.

**Rubric judge:** Claude Opus 4.7 via Anthropic SDK. Judge prompt locked (fixed 5-axis 1-5 scale with anchored examples). Score consistency validated by re-running each rubric on 20% of samples — intra-rater reliability should be ≥0.8 Cohen's kappa.

**Sandbox isolation:** each test runs in a fresh git worktree under `eval/sandboxes/<test_id>/`. Tests never touch real project code.

## Decision thresholds

After running the full eval:

| Outcome | Decision |
|---|---|
| Track A pass rate ≥80%, Track C delta ≥10% | ✅ Ship Qwen as Implementor. OmniGraph provides measurable lift. |
| Track A pass rate 60-80% | ⚠️ Ship Qwen as Implementor with explicit retry/fallback wrapper + Sonnet escalation on failure. |
| Track A pass rate <60% | ❌ Keep Claude Sonnet as Implementor. |
| Track B rubric ≥20/25 consistently | ✅ Qwen can be Drafter for bounded task types. |
| Track B rubric 15-20/25 | ⚠️ Qwen as fallback Drafter (offline / air-gapped scenarios only). |
| Track B rubric <15/25 | ❌ Keep Claude as Drafter. |
| Track D end-to-end green | ✅ Full hybrid (Qwen Drafter→Implementor chain) is viable. |
| Track D fails dependency discipline | ❌ Keep Drafter separate (Claude) + Implementor-only (Qwen). |

## Risks + mitigations

1. **Rubric drift** — Opus 4.7 may score inconsistently. Mitigation: fix rubric prompt, run 20% samples twice, compute κ. If <0.8, re-calibrate rubric with more anchored examples before main run.
2. **Test contamination** — Qwen might have seen public Atelier docs in training. Mitigation: synthesize novel plan.md tasks with domain-specific terminology (Fastbrick canvas nodes as template but different subject).
3. **Tool-retry eval fragility** — mocked MCP server may trigger unrelated errors. Mitigation: run A6 thrice; require 2/3 retries observed.
4. **Budget metric noise** — LM Studio doesn't emit cost; approximate via token count × published rate. Mitigation: report token count as primary, $-equivalent as secondary.

## Estimated effort to build + run

- Harness build (runner, rubric judge, sandbox, aggregator): **~6-8 hours** of focused coding.
- Test authoring (4 Track A + 4 Track B + 4 Track D synthetic tasks): **~4 hours**.
- First full eval run (naked + grounded + Sonnet reference): **~12-16 hours** compute (Qwen is slow on agent loops; Track A alone is ~6 tasks × 3 modes × ~10 min = 3 hours).
- Analysis + REPORT.md: **~2 hours**.

**Total: ~24-30 hours from decision to signed report.**

## What this plan does NOT cover

- **Cost-per-task comparison.** Meaningful but requires an actual billing integration.
- **Latency comparison.** Qwen is slower per token but runs locally — context-dependent.
- **Multi-turn Drafter dialogues (≥10 turns).** B3/B4 are single-pushback tests. A full founder-conversation eval is a v0.2 of this plan.
- **Fine-tuning.** Qwen3.6 base vs meta-profile-SFT comparison is out of scope.

## Next step (when you return)

1. Review this plan + decision thresholds — adjust pass criteria.
2. Pick which track to build first (recommend Track A — mechanical, quickest to verify).
3. I'll build the harness + synthesize test tasks + run.

Open questions for you:
- Do you want Claude Opus 4.7 as rubric judge or prefer Claude Sonnet 4.6 (cheaper, faster)?
- Are the decision thresholds above calibrated right (80% pass rate for "ship")?
- Should meta-profile injection be the whole global_profile.json, or only pre-filtered domain-relevant entries?
- Canvas implementation for D1-D4 — use Atelier's actual MCP server, or a minimal test harness?
