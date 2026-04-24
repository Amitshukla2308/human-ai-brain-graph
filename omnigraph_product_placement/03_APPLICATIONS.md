# Applications — what the extracted schema actually enables

_Written 2026-04-24 as deep-reasoning response to Amit's prompt: "what can be the applications? What is this extraction capable of? What are the real human↔AI problems that we solve that no one is solving?"_

(Editorial note: an earlier draft had a "Founder Boot Journey" as Application 0. That was a misread — the Boot Journey / Product Placement Flow is an **Atelier meta-process that consumes OmniGraph**, not an application of OmniGraph itself. It now lives in `02_METHODOLOGY_NARROW_FIRST.md` and `04_PROPOSED_BUILD_ORDER.md` Step 3 as the primary Atelier-side consumer. The applications below are what OmniGraph *does / enables*.)

## What the schema is (grounding before applications)

OmniGraph is not a memory database. It's a **temporal graph of your cognitive-computational activity with AI**. Every node (entity / concept / decision / rule / mental_move / drift) has provenance, valence, chronology, co-occurrence, authorship. That's a richer object than "stored conversations" — closer to a justified-belief store with a time axis, populated automatically.

Applications below exploit different axes of that graph.

---

## Application 1 — IR + Prompt Compiler

**Two distinct things that share the "IR" name.** They are not the same, and conflating them is dangerous:

### 1a. Light-IR as OmniGraph's prompt-injection output format (in scope, validated)

OmniGraph Vault + Meta-Profile is stored as JSON internally. When the consumer is a **human**, it's compiled to Markdown (vault files, Obsidian-style). When the consumer is an **LLM prompt** (CLAUDE.md, system prompt block, Atelier boot context), it's compiled to **light-IR** — a compact XML-style tagged format documented in `05_LIGHT_IR_OUTPUT_FORMAT.md`.

Benchmarked on qwen3.6-35b-a3b (2026-04-24): **56% token savings on system prompt vs prose, TTFT comparable or better, no output drift, quality preserved.** The compiler is deterministic text templating in Python — no local LLM required.

This is the input-engineering-as-compile-step version of Amit's thumb rule (*output quality = f(input quality × model capability)*), operationalized as OmniGraph's default output format for LLM consumers. Accumulating asset is user-owned; the compiler is free to run on any machine.

### 1b. Per-task LLM-IR compiler (deferred — needs per-user compute)

Gemini's original framing (documented in `01_READING_THE_GEMINI_CONVERSATION.md`): user types a natural-language "vibe" prompt → local 5090-class model compiles it into a hyper-dense operator-syntax IR → cloud model executes deterministically. The compiler handles implicit variable expansion ("retry just in case" → `wrap_retry(target: db_call, max_retries: 3, backoff: exp)`), target resolution, and constraint injection.

**Why deferred:** requires client-side compute (5090-class or equivalent) to run the per-task compilation step. Not portable to users without that hardware. Strong idea for the future; prerequisite doesn't hold for broad distribution today.

**Possible future:** if/when a lighter pre-trained "IR compiler" LoRA on a 4B-class model becomes viable, this unlocks. For now, not in the build order.

### What 1a enables (the relevant thing now)

Given `vault_state` and a caller, the light-IR compiler:
1. Resolves tagged targets against OmniGraph's canonical slug map
2. Extracts relevant Rules / Concerns / MentalMoves for the caller's context
3. Emits a token-bounded light-IR blob formatted for the target consumer (CLAUDE.md / system prompt / Atelier Drafter context envelope)
4. Cross-provider: the same compiled blob works in Claude Code, Cursor, Gemini CLI, Continue.dev — one substrate, many consumers

**Subtle consequence.** The compiler's output quality improves as the Vault grows. Your personal AI gets better with use — but the persistence lives in YOUR layer, not the provider's. Anthropic cannot sell this to you. Nobody can. The accumulating asset is user-owned.

---

## Application 2 — Temporal Intelligence

Chronology unlocks things no other dev-tool does. Notion, Obsidian, Mem, Reflect, Cursor — none of them track these because none of them model sessions as timestamped events with valence + authorship:

**Idea resurrection detection.** An entity first-mentioned 14 months ago, quiet, then suddenly co-mentioned with a current target → you're subconsciously returning to a past idea. Surface: *"Did you have this thought in Jan 2025 on the carlsbert-v1 thread? Context: [excerpt]."* The difference between "new idea" and "resurrected idea" is 10× in founder-utility — resurrected ideas have already survived a filtering pass your conscious mind doesn't remember running.

**Decision half-life.** Time between a Decision being `made_this_session` and its first `revisited` event. If it's <2 sessions on a load-bearing decision, the decision wasn't real — it was a guess wearing decision-costume. Aggregate across decisions = your personal thrashing-coefficient. Nobody measures this about themselves.

**Concern-lifecycle pressure.** 11 latent-unresolved concerns surfaced in Stage-2 aggregation (WSL instability, MCP read_file, Kimi schema adherence, MahaRERA scrape, etc.). These are bugs-you-are-living-with. Most people's mental RAM holds ~3. Externalizing them makes them addressable.

**Affect-precedes-abandonment.** Aggregate per-project: is frustration density in the last 5 sessions before abandonment statistically different from frustration density during active development? Almost certainly yes. Early-warning signal for founder projects on drift.

**Drift-rate correlates with AI-fatigue.** Correlate drift rate against session-of-day, session-length, day-of-week. Hypothesis: your 3rd evening session has 2-3× the drift rate of your morning session. Once measured, you can structurally cut at drift-threshold rather than at exhaustion-threshold — which is usually past the point of good decisions.

---

## Application 3 — Truth-Maintenance System (revived 80s AI concept)

**The classic idea.** A database where every belief has justification-edges to other beliefs. If a justifying belief gets invalidated, dependent beliefs auto-flag for revisit. Never worked in the 1980s because beliefs had to be hand-entered.

**The revival.** Your Vault IS a justified-belief store, populated automatically from real work. Decisions have `why`, `alternatives_considered`, `related_entities`. When a related entity's status changes (deprecated, renamed, flagged concern_raised), downstream Decisions that depended on it can be surfaced: *"This decision depended on X; X is now in concern_raised state. Revisit?"*

No founder has a working TMS over their own decisions. Most of us lose the dependency graph of our own reasoning within weeks. "I decided Y because Z" becomes "I decided Y" within a month; within a quarter it becomes "Y is the right answer"; by then Z may no longer hold but Y persists uncritically.

Having a TMS could be the difference between *"I keep making the same mistake"* and *"I no longer make that mistake because the condition is flagged the moment it recurs."*

---

## Application 4 — Present-Moment Wisdom (requires real-time Atelier feed)

**The big multiplier.** When OmniGraph becomes retrospective + real-time (Atelier feeds sessions in as they happen), it stops being memory and becomes **wisdom-at-pressure**.

In-session surfacings:
- *"You're entering a drift pattern you had on session X, which led to Y (abandoned). Pause?"*
- *"This is the 4th time you've raised concern Z without resolving. Address or park explicitly."*
- *"Rule 'simplicity first' applies here; the current path is adding a dependency."*
- *"Your numbered-directive style usually precedes shipping velocity; exploratory 'let's see' style usually precedes scope expansion. Mode check?"*

This is the Carlsbert v2 soul architecture but with actual substrate behind it. Not rules hand-authored from theory — rules *extracted from you*. Trustable because they're yours.

**The Atelier ↔ OmniGraph loop closes here.** Atelier captures → OmniGraph extracts → OmniGraph surfaces → Atelier routes. Without OmniGraph, Atelier's agents are reading from theory. With OmniGraph, they're reading from the founder.

---

## Application 5 — Meta-Cognitive Prosthesis (stops being dev-tool, becomes cognitive aid)

Zooming out past developer productivity:

**Externalized working memory as reasoning cache.** *"I already decided X, with reason Y, 3 weeks ago"* becomes *addressable* rather than re-derived under pressure. For anyone with executive-function load (parents, neuro-divergent folks, founders wearing many hats), this is functional. Not a to-do list — a **reasoning cache.**

**Personal-AI-relationship contracts.** Each developer learns tacit contracts with their AI ("when Claude says 'let me check', it does"; "when Sonnet offers 3 options, option 2 is usually right"). These are invisible, costly to build, and reset with every model upgrade. OmniGraph's confirmed `mental_moves_ai` + drift taxonomy makes them explicit. Portable. Upgradable.

**Re-derivation tax elimination.** Every new chat, you re-explain context. The fix isn't "better memory in the AI" (Anthropic's Memory feature is session-scoped, still). The fix is *your layer* pre-digesting and injecting. No one solves this because the substrate required is the 2+ year history of conversations the user already owns but hasn't extracted.

**"My AI knows me" fiction.** Every major AI product markets personalization; in reality it's session-scoped. Across sessions, you're a stranger every time. OmniGraph is the only mechanism that gives you a *persistent AI relationship* because the persistence lives in your layer.

---

## Three human↔AI problems that no one else is solving

Consolidated from above:

### 1. Re-derivation tax

Hours/week developers waste re-explaining themselves to AI. Memory features (Anthropic, OpenAI) are provider-scoped and session-scoped. OmniGraph + compiler is the only path to **cross-provider, cross-session persistence where the user owns the layer**. The more models and tools you use, the more acute this tax gets — and cloud-provider memory cannot solve it because each provider sees only their slice.

### 2. Silent-failure compounding

Most AI failures aren't explicit errors — they're subtle wrong-premise agreements, hallucinated confidence, silent truncation, rationalized-after-the-fact tool-selection. Aggregated concern-raised-never-resolved + drift-by-trigger patterns make these visible at a *population-of-one* level. No dev tool shows you *your* AI failure taxonomy. Cursor/Copilot/Claude Code show the AI their best face; only you can see where it fails *for you*.

### 3. Cognitive cost of multi-model, multi-tool stack

Cursor + Claude Code + Cline + Antigravity + ChatGPT desktop each have different tacit contracts, strengths, failure modes. Cross-provider normalization (which we've demonstrated works — P6 cross-provider bleed in Stage-2 output) means **one profile that works across the stack**, not five. This is the killer feature for anyone using >2 AI tools seriously. Nothing in market targets this shape because the market treats each tool as a standalone surface rather than a substitutable backend for the same user.

---

## Market gap analysis — why nothing else touches this

- **Notion / Obsidian / Mem / Reflect** — store. Don't extract schema, don't track chronology with valence, don't compile to target prompts.
- **Anthropic Memory / OpenAI Memory / Cursor Chat Memory** — provider-locked, session-scoped, not extractable. Can't compound across providers.
- **Cursor rules / CLAUDE.md / .cursorrules** — hand-authored, static, per-project. Updates require human maintenance.
- **Cognitive tools for ADHD/executive function (Todoist, Reclaim, etc.)** — store tasks, not reasoning cache. Surface what to do, not why previously.
- **Developer productivity analytics (Waydev, LinearB, Swarmia)** — measure git output. Not cognitive patterns.
- **Agent frameworks (LangChain, AutoGPT, CrewAI)** — orchestrate calls. No memory of how *you* prefer to work with them.

**The gap:** a personal, portable, model-agnostic layer that captures your AI-interaction history and makes it addressable in real-time via compilers to whatever tool you're using. OmniGraph + prompt compiler + Atelier boot journey is this shape. As far as I can see, nothing in market targets this exactly.

---

## The unifying thesis

OmniGraph is the first product where:
- **The asset grows by using it** (compounding-with-use, not static store)
- **Owned by the user** (not rented from provider)
- **Compatible across the entire AI stack** (cross-provider, cross-session)
- **Addressable at pressure** (real-time surfacings, not offline reporting)

Every other AI-personalization play is *grow value for the provider who then rents you access*. The ownership inversion is the defensible thing, and it's only possible because the extraction substrate is the user's historical conversations, not the provider's internal logs.

The **IR + compiler move** makes the value portable. Without them, OmniGraph is a private diary. With them, it's a personal operating system layer.

The **founder boot journey** makes the value visible. Without it, OmniGraph is abstract infrastructure. With it, it's a UX moment every founder remembers — the session where their own patterns greet them at the threshold of a new project.
