# OmniGraph product placement — discussion trail

Five files, chronological by when each thought-beat happened in the 2026-04-24 session. Read in order or jump — each stands alone.

## Layering declaration

**Atelier — powered by OmniGraph.** OmniGraph is the *knowing layer* (substrate: Vault + Meta-Profile + IR compiler). Atelier is the primary UX over that substrate. They are distinct: OmniGraph is consumable by other AI tools (Cursor, Claude Code, Gemini CLI, Continue.dev) as well; Atelier is the commercial/UX showcase. The relationship is like Git → GitHub, Kubernetes → Rancher, file system → Finder: the UX wraps the substrate; the substrate survives outside the UX.

Toggles exposed through Atelier (Product Placement Flow, boot injection, concern surfacing, real-time drift warnings, cross-provider sync) are how founders configure *how much of OmniGraph* they want active in their Atelier workflow. Monetization / distribution details deliberately parked.

## Files

1. **`01_READING_THE_GEMINI_CONVERSATION.md`** — What I observed when Amit shared his 8-month-old Gemini chat about a similar idea. Five things potentially missed in the current omnigraph build: project-agnostic framing, Layer 0 positioning, exhaust-data economics, Agent Territories discipline, small items.

2. **`02_METHODOLOGY_NARROW_FIRST.md`** — Amit's deliberate move: withhold broader ambition until narrow project-scoped build is done. Three-role workflow (brainstorm / organize / execute). "Sugarless coffee first, then sugar" metaphor. Projection-ladder for how abstract the derived views should be for different consumers.

3. **`03_APPLICATIONS.md`** — Five application families the extracted schema enables (IR + prompt compiler, temporal intelligence, truth-maintenance system, present-moment wisdom, meta-cognitive prosthesis). Three human↔AI problems no tool in market currently solves. Market-gap analysis.

4. **`04_PROPOSED_BUILD_ORDER.md`** — Sequencing suggestion for moving from current substrate → compiler → Product Placement Flow integration in Atelier → real-time loop. Dependency order, not calendar order.

5. **`05_LIGHT_IR_OUTPUT_FORMAT.md`** — Empirically validated light-IR prompt-injection format (XML-tagged, ~56% token savings vs prose, benchmarked on qwen3.6-35b-a3b). The default output format OmniGraph's compiler targets for LLM consumers; Markdown remains the default for human-audit consumers.

6. **`06_DEVELOPMENT_PLAN.md`** — Concrete file+line development plan over the current codebase (`qwen_pipeline.py`, `phase4_scale.py`, `stage2_aggregate.py`). 8 phases (0 → 7), ~20-25 days total. Evaluated against reliability + simplicity at every step.

7. **`07_BRAIN_VIZ.md`** — Anatomical wireframe brain rendering (Prefrontal / Motor / Hippocampus / Amygdala / Brainstem / Sensory / Anterior Cingulate / Corpus Callosum) as the visible organ of founder↔AI cognition. All 10 diagnostic hypotheses as overlay modes. Frontend built in Claude Design (desktop app) + Claude Artifacts; backend is HyperRetrieval signals + deterministic hypothesis engine. Per-export sanitization (None / Named-stripped / Aggregated).

## The Product Placement Flow (meta-process derived from this folder)

The arc of these five files is itself the **reference exemplar** of a repeatable process — a 6-phase founder thinking exercise for placing a project as a product. Every Atelier project will be offered this flow at boot (skip option + "complete later from project settings / X path" available). See `02_` for the generalized 6-phase structure.

Status: discussion draft. Next steps: more OmniGraph applications, data-sourcing + ETL artifact structure, architecture for scale (including ripple/hyperretrieval-on-artifacts for multi-year corpora).
