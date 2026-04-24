# OmniGraph session recap — what / why / how

Chronological, ~10 beats. Captures the actual arc, not the noise.

## 1. Pivot from Atelier to "knowing" first
**What:** Paused Atelier Phase A+B+C. Set up omnigraph in `/projects/omnigraph/` with 700+ AI conversations from 5 providers in `/ai_conversations/`.
**Why:** Hit the realization that Atelier's personal brain / domain brain needs substrate — you can't build the next thing without the knowing layer. The session itself was a demonstration of what Atelier is supposed to automate (you pour thoughts, I scribe + structure).
**How:** Started by reading the atelier `JOURNAL.md` as the oracle — a hand-crafted artifact demonstrating what the output should look like. Derived schema from that, not from abstract design.

## 2. Schema design — journal-first
**What:** Schema v0.1 drafted with 10 object types (Entity, Decision, Drift, MentalMove, Rule, Stance, Affect, MetaMoment, CognitiveDual, Artifact). Hand-traced 3 journal paragraphs to validate.
**Why:** The journal had already demonstrated what the Vault + Meta-Profile should contain. Reverse-engineering from the demonstrated artifact is sturdier than designing from first principles.
**How:** `docs/SCHEMA.md` v0.1 + validation section showing decomposition of real journal excerpts into schema instances.

## 3. Honest read on Qwen capability
**What:** Pushback when you asked "can Qwen handle this?" — tiered answer: Tier A (entity extraction) easy; Tier B (drift/affect/moves) noisy; Tier C (rule synthesis, level tagging) unreliable alone. Proposed loops-with-grounding to close the gap.
**Why:** A 35B model needs different scaffolding than a frontier model for subjective reasoning. Better to be honest than to set up an apples-to-oranges comparison.
**How:** Web-searched actual Qwen3.6-35B-A3B benchmarks (AIME 92.7, SWE-bench 73.4, GPQA 86.0) and Huang 2023 self-correction research. Proposed grounded-loop pipeline (transcript as external signal).

## 4. You caught false authorship — schema v0.2
**What:** First oracle extraction recorded referenced context ("Fastbrick canvas has 12 approved nodes") as if the session had authored it. Would've produced false-authorship in the Vault at scale.
**Why:** Extraction conflated two things: *what this session authored* vs *what this session referenced*. Both are real, but must be distinguished.
**How:** v0.2 introduced `MentionEvent` as the atomic unit (every reference recorded, chronology preserved) + delta-gating for `Decision/Drift/Rule/MentalMove/Stance/Affect/MetaMoment` (only when authored-this-session). Re-extracted the test session cleanly.

## 5. You pushed back again — chronology is signal
**What:** When I framed it as "skip context, keep delta," you asked: "what about the chronological effect? if something gets mentioned 50 times over a month then stops — did the user give up or did AI get it?"
**Why:** Binary delta/context would throw away the most interesting signal. The pattern of mentions over time tells you about convergence, abandonment, internalization, rename, concern lifecycle, cross-provider bleed.
**How:** Added 6 Stage-2 inference patterns (P1-P6) computed over MentionEvent streams. Schema v0.2.1 locked. "Still on path?" check mid-design protected against endless polish.

## 6. Pilot oracle + Qwen pipeline — empirical iteration
**What:** 25 sessions extracted by me (oracle, hand-authored) across 5 providers. Then Qwen pipeline built (7 phases: narrow 1a-1e → grounded verify → adversarial critique → synthesis). Ran it on same 25 sessions.
**Why:** Oracle provides the reference. Qwen provides the scale. Their gap tells us what pipeline + prompts need to improve.
**How:** `src/qwen_pipeline.py` with LM Studio @ `192.168.88.2:1234`. Thinking-mode budget trap caught on first run (finish=length, content=0) — bumped token budgets. Three prompt pivots applied and validated (BIOS session went 0→4 drifts with root-cause depth stronger than my oracle).

## 7. COMPARE surprise — Qwen's slug discipline beat oracle
**What:** Qwen produced cleaner canonical target_ids across providers than my hand-authored oracle. P6 cross-provider matches: oracle 0, Qwen 14. P1 convergence targets: oracle 4, Qwen 60.
**Why:** Frontier models aren't the ceiling on every dimension. A smaller model can have systematic advantages in specific sub-tasks (here: slug normalization was disciplined in Qwen's output because a fresh mind doesn't carry my inconsistent id conventions).
**How:** `pilot/COMPARE.md` documents the 5 systematic findings + decision thresholds for scale-up.

## 8. Overnight autonomous scale-up
**What:** Phase 4 ran 4 providers to completion (Claude Desktop 15/15, Gemini CLI 21/21, Cline 91/91, Antigravity 76/101) = 183 sessions. Four non-breaking pivots applied in-flight with rollback paths preserved.
**Why:** Overnight compute was free. Corpus coverage is a prerequisite for Stage-2 having real signal.
**How:** 100+ wake cycles (`ScheduleWakeup`) at 270s cadence to stay in prompt cache. Pivots tracked in `OVERNIGHT_STATE.json`. Morning handoff written before user returned.

## 9. Three-axis insight (your messages surfaced this)
**What:** "Can Qwen replace Drafter/Implementor?" is never a 1D question. Three axes: **raw capability × orchestration harness × per-task economics.** Same input comparisons measure one axis; real product decisions need all three.
**Why:** Claude Sonnet in Claude Code ≠ raw Sonnet. Atelier IS Qwen's equivalent of Claude Code. Local Qwen has unlimited per-task compute — self-consistency / ensembling become free, flipping economics asymmetrically.
**How:** Updated `EVAL_PLAN.md` to v1.1 with Track E (input-engineering gap analysis) + Track C reframe (naked vs grounded ablation). Saved as umbrella memory for future eval work.

## 10. Incidents + discipline
**What:** Two operational mistakes: (a) parallel agent spawn defaulted to regex scripts instead of per-session reasoning — burned ~150K tokens, you stopped it; (b) LM Studio model-swap attempt risked OOM — you caught it.
**Why:** First was a prompt-design failure (didn't force tool-path per session). Second was treating a local single-GPU server like a stateless cloud API.
**How:** Cleaned up ~350 regex outputs to quarantine. Wrote RCA + hard guardrails for local model servers. Locked Option 3 (30 signal-rich outliers on the loaded model, no swap) as the closing Phase 4 plan.

## Where we are now

- Outlier batch running in bg (`bs4t89d8s`) on loaded qwen3.6-35b-a3b. 40 sessions, ~2hr.
- Schema v0.2.1 locked. Oracle (25) + Qwen Phase 4 (183) + outliers (40) = ~248 sessions extracted when batch completes.
- COMPARE.md, EVAL_PLAN.md v1.1, SCHEMA.md, RCA, overnight report — all on disk.
- 7 memories saved (see `~/.claude/projects/-home-beast-projects-omnigraph/memory/MEMORY.md`):
  - Three-axis model equivalence (umbrella)
  - Orchestration framework is part of model capability
  - Input quality × model capability thumb rule
  - Amit catches false simplification
  - Register calibration — match the work, not fear
  - Don't switch LM Studio models mid-workflow
  - Hard guardrails for local model servers

## The arc, one line

**Goal was Atelier → realized needed substrate → built omnigraph v0.2.1 → 208-248 sessions extracted → three-axis insight reframes everything → ready for Atelier Phase B with a real knowing-layer.**
