# Proposed build order

_Written 2026-04-24 as closing thought on the product-placement discussion. Dependency order, not calendar order. User holds final sequencing authority._

The application that most clearly anchors everything else is the **Product Placement Flow** in Atelier (see `02_METHODOLOGY_NARROW_FIRST.md` for the 6-phase structure). It converts abstract Meta-Profile into concrete founder-facing UX, is offered at every new project boot in Atelier (with skip + "complete later from project settings" options), and forces us to complete the pieces that matter most for near-term product value.

## The build-order logic

Each step must produce a working artifact another step can consume. No "foundation layers" that take weeks without a user-visible surface.

### Step 1 — IR contract lock (1-2 days, mostly documentation)

**What.** Explicitly declare OmniGraph's output as an **Intermediate Representation** with a versioned schema contract. Document what compilers can expect.

**Why.** Right now, v0.2.1 is a schema — but nobody has declared "this is the contract; compilers target it." Before building compilers, the contract needs a name and a stable shape.

**Artifact.** `omnigraph/docs/IR_CONTRACT.md` — lists the Vault and Meta-Profile as typed projections, documents the invariants, specifies the JSON shape each projection exposes.

**Dependency.** None. Pure documentation move.

### Step 2 — Meta-Profile projection compiler (2-3 days)

**What.** The first compiler: `MetaProfile.toCompact(max_tokens) → string`. Takes the full global_profile.json and produces a token-bounded compact summary suitable for injection into a system prompt or CLAUDE.md.

**Output surfaces:**
- `omnigraph compile --target claude-code` → writes to target project's CLAUDE.md
- `omnigraph compile --target gemini` → writes GEMINI.md
- `omnigraph compile --target cursor-rules` → writes .cursorrules
- `omnigraph compile --target boot-journey` → structured JSON for Atelier to render

**Why.** This is the smallest useful compiler. One well-built projection unlocks immediate usefulness across multiple AI tools and produces the data format Atelier's boot journey needs.

**Dependency.** Step 1 (IR contract) must be locked first.

### Step 3 — Product Placement Flow in Atelier (3-5 days)

**What.** At new-project boot in Atelier, offer the founder a 6-phase Product Placement Flow (per `02_METHODOLOGY_NARROW_FIRST.md`). Reads the compact Meta-Profile compiled in Step 2; surfaces relevant mental moves, standing rules, latent concerns, drift warnings, abandonment patterns, project-scoping templates as interactive cards. The founder confirms / edits / skips each surface; selected content becomes the injected context for the project's first Canvas draft. Flow output = the project's placement charter (vision → methodology → applications → build order → lock).

**UX behavior:**
- **Prompt at project boot** — offered as the first post-org-selection screen.
- **Skip option** — founders can skip and go straight to Canvas. No forced friction.
- **Deferred completion** — skipped flows are reachable later from project settings / "product placement" path. Not gated, not hidden, not nagging.
- **Re-run at pivot moments** — founder can re-open the flow when feeling drift or considering a pivot, re-run selected phases without redoing everything.

**Why.** The anchor application. Makes Meta-Profile concrete UX that a founder remembers. Differentiates Atelier from every other "start a new project" flow. Prevents first-week scope drift that kills most founder projects.

**Dependency.** Step 2 (projection compiler) must produce the flow's input JSON target. Requires modest Atelier UI work (new view, 6 phase cards, skip/defer/re-run actions, charter-output view).

**Out of scope for this step:** real-time ingestion. The flow uses OmniGraph's offline-computed global_profile. Real-time is Step 5.

### Step 4 — Prompt compiler v0.1 (3-5 days)

**What.** `compile(intent: string, vault_state: IR) → { prompt: string, model: string, tools: string[] }`. Given a user intent and current IR state, emit the compiled prompt + model routing + tool selection for a single agentic call.

**Rollout.** First as a CLI tool (`omnigraph compile-prompt "<intent>"` prints the result). Then wire into Atelier's Drafter as the default prompt-construction step.

**Why.** Operationalizes the input-quality × model-capability thumb rule. Decouples founder intent from model-specific prompt engineering. Atelier's Implementor gains a calibrated scaffolded input rather than raw founder text.

**Dependency.** Step 2 (projection compiler — needed for context slicing). Can overlap with Step 3.

### Step 5 — Real-time ingestion loop (5-7 days)

**What.** Atelier captures live session output; OmniGraph's extractor runs incrementally on new turns; Stage-2 aggregation updates asynchronously; boot-journey Meta-Profile + prompt compiler receive updated IR within minutes of a session ending.

**Why.** Converts OmniGraph from retrospective memory to **present-moment wisdom** (see `03_APPLICATIONS.md` §4). Unlocks the in-session surfacings: drift warnings, concern-lifecycle nudges, rule-firing at pressure.

**Dependency.** Steps 2 + 4 must exist. Requires Atelier hook into session-end events. Requires incremental-update logic in the extractor (currently full-session extraction).

### Step 6 — Temporal-intelligence surfaces (1-2 weeks, can roll out incrementally)

**What.** Build the queries that make chronology useful:
- Idea-resurrection detection
- Decision half-life aggregates
- Concern-lifecycle dashboard
- Affect-precedes-abandonment early warning
- Drift-rate-by-session-of-day correlations

Each is a small query over the Vault + MentionEvent stream, rendered as a card in the Atelier dashboard.

**Why.** These are the features that justify OmniGraph's existence beyond "memory injection." They're the things Notion/Obsidian/Mem fundamentally cannot do.

**Dependency.** Step 5 (real-time) makes these useful in-session; offline versions work with just the extracted corpus (already done).

### Step 7 — Truth-Maintenance System (2+ weeks, research-y)

**What.** Track dependency edges between Decisions and related entities. When related-entity status changes (deprecated, renamed, concern_raised), auto-flag downstream Decisions for revisit.

**Why.** Highest-leverage long-term feature — the first working TMS over a working developer's real decisions.

**Dependency.** Step 6 partially. This is where we invest after the core product surface is proven.

### Deliberately NOT in the early order

- **Codex / high-sugar projection layer** (shareable, anonymized meta-profile). Valid product, not near-term leverage. Build after Boot Journey has real users.
- **Multi-user aggregation / federated patterns.** Requires multi-user installed base first.
- **Protobuf decryption for Antigravity .pb files.** Parked. 76/101 AG sessions already captured via artifact extraction; the remaining 25% is not critical path.
- **Claude Code full-corpus extraction (476 remaining).** Representative coverage is enough for current application needs. Revisit if Boot Journey quality suggests more substrate needed.

## Why this order maximizes early value

1. **Steps 1-3 land within a week and produce a user-facing feature** (Boot Journey) that demonstrates OmniGraph's value concretely. Founders will either be impressed or they won't; either way we learn.
2. **Step 4 (compiler) wires OmniGraph into every new Atelier agent call** without requiring real-time ingestion. Payoff scales with every Atelier session.
3. **Step 5 (real-time) is only justified once steps 1-4 prove demand.** If boot journey feels gimmicky in practice, don't invest in real-time loop.
4. **Steps 6-7 are feature-multipliers** that extend the core — they don't create the core.

## What this order is not

- Not a prescription. Amit holds sequencing authority (per the methodology in `02_`).
- Not calendar-committed. Dependency order, not promises.
- Not exclusive. Work on Atelier Phase A+B+C proceeds in parallel; OmniGraph integration points are additive to Atelier's roadmap, not replacements.

## Open questions that gate sequencing

1. **Boot Journey scope.** 5-6 surfaces, or start with 2-3 (confirmed mental moves + rules) and add the rest as feedback suggests?
2. **Compiler target priority.** Claude Code / Atelier first (the founder's current primary tool), or cross-target from day 0 (Cursor + Gemini + Claude in parallel)?
3. **Real-time ingestion architecture.** Webhook-style (Atelier POSTs to OmniGraph), queue-based (SQLite → polling), or library-embedded (Atelier calls OmniGraph directly)?
4. **Where does the compiler live?** Separate binary, Atelier plugin, MCP server?
