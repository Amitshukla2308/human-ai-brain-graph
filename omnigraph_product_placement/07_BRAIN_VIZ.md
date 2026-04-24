# Brain Viz — anatomical wireframe of the founder↔AI cognitive system

_Written 2026-04-24. Frontend target: **Claude Design** (in the Claude Desktop app) for UI generation; **Claude Artifacts** for interactive React preview and iteration. Not HyperRetrieval's chainlit stack — HR is the **data backend** only (Phase 5a)._

## What this is

A wireframe anatomical brain rendered in-browser, where anatomical regions are semantically mapped to OmniGraph schema types. Artifacts (mentions, decisions, concerns, rules) become neurons; co-mentions become synapses; Stage-2 inferences become overlay patterns lighting up the regions.

The viz is the **visible organ** of a founder's cognitive-computational activity with AI — a mirror that makes the invisible substrate inspectable, shareable (with sanitization), and diagnostically useful.

---

## Region ↔ schema mapping (fixed anatomical layout)

| Region | Schema type it renders | Visual behavior |
|---|---|---|
| **Prefrontal cortex** | Decisions, Plans, Stances | Bright when load-bearing decisions recent; dim under thrash |
| **Motor cortex** | Actions / Executed tasks / Commits | Flashes on ship events |
| **Hippocampus** | Resurrected entities, long-dormant targets | Pulses when idea-resurrection detected |
| **Amygdala** | Affect markers (frustration, excitement) | Color-temperature maps to valence density |
| **Brainstem** | Tool calls, MCP invocations, shell actions | Steady baseline, spikes on tool storms |
| **Sensory cortex** | Incoming inputs (providers, pastes, files) | Per-provider subregion lights per session |
| **Anterior cingulate** | Concerns (latent/raised/unresolved) | Warmer hue as unresolved concerns accumulate |
| **Corpus callosum** | Cross-project / cross-provider co-mentions | Bright fibers when bleed is detected |

Anatomy stays **fixed** — humans pattern-match to it instantly. Data modulates density, color, firing; never position.

---

## The 10 diagnostic hypotheses (all shipped at launch)

Each hypothesis is an overlay mode. A dropdown / sidebar toggles them. Each renders as a specific firing pattern + a one-line verdict card.

### Collaboration-health (3)

1. **Rehearsal vs commitment.** For Decisions: decision-half-life distribution (time made → first revisited). Short half-life → Prefrontal pulses rapidly → verdict: "Many decisions are being re-opened within 2 sessions."
2. **Concern debt.** Anterior cingulate heat map of raised-but-unresolved concerns. Verdict names the top 3 longest-open.
3. **Affect-precedes-abandonment.** Amygdala frustration density in the last 5 sessions of each abandoned project vs active projects. Verdict flags projects whose amygdala pattern matches prior abandonments.

### Cognitive-load (3)

4. **Drift-rate by session-of-day.** Prefrontal↔Motor coherence across session time buckets. Verdict: "Evening drift rate is 2.3× morning."
5. **Concurrent-project pressure.** Count of actively-firing projects per week. Verdict: "Above-3 projects/week correlates with 40% higher drift."
6. **Tool storm.** Brainstem spike density per session. Verdict: "Top 10% tool-storm sessions produced 30% of your concerns."

### Cross-project / cross-provider (2)

7. **Cross-pollination vs bleed.** Corpus callosum signal — is cross-project co-mention productive (shared infra insight) or leaky (scope creep)? Verdict classifies top fibers.
8. **Provider-specific cognition.** Sensory cortex subregions colored by valence: does your Claude-Code self differ from your Gemini-CLI self? Verdict: "You raise 3× more concerns on Antigravity; you ship 2× faster on Claude Code."

### Tool-fit (2)

9. **Rule-firing at pressure.** Do your standing rules (extracted MentalMoves / Rules) fire more when shipping-pressure is on or off? Prefrontal + Motor co-activation under pressure. Verdict: "Simplicity-first fires 4× more in morning sessions."
10. **Silent-failure pattern.** Aggregate Decisions whose `related_entities` later changed status (deprecated/concern_raised). Prefrontal nodes whose dependencies are stale. Verdict: "5 decisions rest on now-deprecated premises."

Each overlay is additive — user can stack 2-3 to see correlations (e.g., #4 drift + #6 tool-storm).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 5a: HyperRetrieval over Vault (internal, code, no UI)│
│   Input:  pilot/vault/*.md + pilot/events/*.jsonl          │
│   Output: graph.json, cochange.json, communities.json,     │
│           criticality.json, granger.json                    │
└──────────────────────┬──────────────────────────────────────┘
                       │  exports via src/viz/export_viz_state.py
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Viz data contract (single JSON file, < 500KB typical)       │
│   pilot/viz/brain_state.json                                │
│   {                                                          │
│     regions: [{id, anatomical_coords, density, color_temp}],│
│     neurons: [{id, region, size, valence, last_fired_ts}], │
│     synapses: [{from, to, weight, cross_region}],          │
│     hypotheses: { "1_rehearsal": {firing_pattern, verdict},│
│                   "2_concern_debt": {...}, ... },          │
│     timeline: [{ts, fired_neurons}]  // for animation      │
│   }                                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │  served locally via FastAPI at /brain/state
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 5b: Brain viz frontend (React, Claude-Design-built)   │
│   - Anatomical SVG wireframe (fixed, hand-authored once)   │
│   - Neuron/synapse overlay (Canvas / D3)                   │
│   - Hypothesis engine renderer (overlay modes)             │
│   - Sanitization-on-export (per-export user choice)        │
└─────────────────────────────────────────────────────────────┘
```

**Why split:** Phase 5a is data-side code; Phase 5b is pure frontend. They're independently testable and ship in different mediums.

---

## Hypothesis engine (backend, Python)

**File added:** `src/viz/hypotheses.py` (~400 lines, 10 functions)

Each hypothesis is a pure function:
```python
def h1_rehearsal(vault_state, events) -> {
    "firing_pattern": {"prefrontal": [neuron_ids...], "intensity": 0.7},
    "verdict": "Many decisions are being re-opened within 2 sessions.",
    "top_evidence": [{"neuron_id": "d_xyz", "days_to_revisit": 1.2}, ...],
}
```

They read Vault + events + HR-exported graph signals (co-change, criticality, communities). Output is folded into `brain_state.json` under `hypotheses[key]`.

**Reliability / simplicity lens:**
- ✅ Each hypothesis is isolated. Turn off any one without breaking others.
- ✅ Deterministic. No LLM in the hypothesis path. Trustworthy.
- ⚠️ Evidence threshold matters — a hypothesis with <10 data points should render as "insufficient data", not a false verdict.

---

## Export / sanitization (per-export user choice)

Three levels (per `02_METHODOLOGY_NARROW_FIRST.md` sugar-ladder):

| Level | What's sanitized | Use case |
|---|---|---|
| **None** (default local) | nothing | Your own dashboard |
| **Named-entities-stripped** | project/entity names → anonymized tokens; structure preserved | Share with advisor |
| **Aggregated-only** | no neurons, only region densities + hypothesis verdicts | Public tweet-ready screenshot |

User picks at export time. Default is the safest (Aggregated). Sanitization is client-side before any file is emitted.

**File added:** `src/viz/sanitize.py` (~100 lines).

---

## Frontend build plan — Claude Design (desktop app) + Claude Artifacts

### How Claude Design works (from Anthropic docs as of 2026-04)

- **Claude Design** is a feature in the Claude Desktop app that consumes your uploaded assets (component libraries, Figma exports, brand files) and produces a **design system** (UI kit): color palette, typography scale, component tokens. This becomes the palette Claude draws from when it generates UI in a conversation.
- **Claude Artifacts** is the interactive React/HTML side-panel in the same app where Claude emits runnable UI. Artifacts support React + Tailwind + a curated set of libraries (`recharts`, `lucide-react`, shadcn/ui primitives). SVG is first-class.
- **Workflow:** establish a Design (the kit), then ask Claude to generate an Artifact that uses tokens from that kit. You iterate in the side panel — the preview is live; you click/navigate/interact.

### What to build in Claude Design itself

**Upload to Claude Design (one-time, ~15 min):**
1. A 1-page **palette brief**: cognitive / anatomical visual language — deep neutral background (slate-950), firing-neurons in a temperature ramp (cool-cyan → warm-amber → hot-red), region outlines in low-contrast off-white, accent in a single signature brand color.
2. **Typography:** one mono (for verdict cards / data readouts — JetBrains Mono or Geist Mono) + one sans (for labels / controls — Inter or Geist Sans). Two weights max.
3. **Component tokens:** panel (glass/dark), pill (for hypothesis toggles), verdict card (large numeral + one-line sentence), tooltip, sliver-sidebar.

Once Claude Design has the kit, it becomes the implicit style context for every Artifact you generate in the same workspace.

### What to build in Claude Artifacts (iteratively, over a few conversations)

Ask Claude (in the desktop app, with Design active) to generate these Artifacts in order. Each is a single React component. **Stub points** are data the Artifact hardcodes; **wire points** are the exact interfaces the real backend will replace those stubs with.

#### Artifact 1 — `BrainWireframe.tsx` (pure SVG, no data)

A single React component rendering the anatomical outline in SVG, labeled regions, no neurons yet.

- **Stub:** none (static SVG).
- **Wire:** none. This is the chrome.
- **Prompt to Claude:** "Generate an SVG component of a side-profile human brain, anatomical wireframe style, with 8 labeled regions (Prefrontal, Motor, Hippocampus, Amygdala, Brainstem, Sensory, Anterior Cingulate, Corpus Callosum). Each region is a `<path>` with `data-region={id}` and a subtle stroke. Background slate-950. Use tokens from the design system."

#### Artifact 2 — `NeuronLayer.tsx` (data-driven overlay)

Renders neurons as circles + synapses as curves on top of `BrainWireframe`.

- **Stub:** a hardcoded `MOCK_BRAIN_STATE` object inline at the top of the file, matching the **exact shape** of `pilot/viz/brain_state.json` (see contract above). Include ~30 neurons, ~40 synapses, all 10 hypotheses with plausible verdicts. This stub is what the user eyeballs during Claude Design iteration.
- **Wire:** one function — `useBrainState()` hook. In the stub version, it returns `MOCK_BRAIN_STATE`. In production, replace its body with `fetch('http://localhost:8787/brain/state').then(r => r.json())`. **This is the only wire point in the whole Artifact.**
- **Prompt to Claude:** "Extend BrainWireframe with a NeuronLayer. Accept a `brainState` prop matching this TypeScript interface: [paste the contract]. Render neurons as filled circles whose fill is a temperature color from the `color_temp` field. Render synapses as quadratic bezier curves between their endpoints with opacity proportional to `weight`. Neurons pulse (CSS animation) if `last_fired_ts` is within the last 5 minutes of the timeline."

#### Artifact 3 — `HypothesisSidebar.tsx` (interaction)

The left/right rail with 10 hypothesis toggles + verdict card for the active hypothesis.

- **Stub:** reads `brainState.hypotheses` (same mock).
- **Wire:** none additional — piggybacks on `useBrainState()` from Artifact 2.
- **Prompt to Claude:** "Build a sidebar with 10 pill toggles, one per hypothesis keyed by `hypotheses[key].id`. Clicking a pill sets an active overlay. Below the pills, render a verdict card showing the active hypothesis's `verdict` (one-line) and top 3 items from `top_evidence`. Allow multi-select (up to 3 stacked overlays). When multiple active, blend their firing_patterns."

#### Artifact 4 — `Timeline.tsx` (temporal scrubber)

Horizontal scrubber at the bottom; dragging replays the firing sequence.

- **Stub:** `brainState.timeline`.
- **Wire:** none additional.
- **Prompt to Claude:** "Add a horizontal timeline scrubber using the `timeline` array. Each tick represents a session. Dragging sets a currentTime; neurons whose `last_fired_ts` is within a 1-hour window of currentTime render active, others fade. Include play/pause and 1x/4x/16x speed controls."

#### Artifact 5 — `ExportDialog.tsx` (sanitization UI)

Three-option modal for export.

- **Stub:** a fake `onExport(level)` that logs to console.
- **Wire:** replace `onExport` with a call to backend `POST /brain/export {level}` which returns a file stream. The frontend just calls this — the sanitization itself lives in Python (`src/viz/sanitize.py`).
- **Prompt to Claude:** "Modal with three radio options: None / Named-entities-stripped / Aggregated-only. Each option shows a 1-sentence explanation of what's stripped and what's preserved. Confirm button calls `onExport(level)`."

### Wiring checklist (after Design phase is done)

Take the Artifacts, drop them into a standalone React project (Vite scaffold — Claude Artifact Runner works, or new Vite app). Then:

1. Stand up `src/viz/serve.py` — FastAPI on `localhost:8787` exposing `GET /brain/state` and `POST /brain/export`. Reads `pilot/viz/brain_state.json`. Writes sanitized exports to `pilot/viz/exports/`.
2. Replace `useBrainState()` stub with real `fetch`.
3. Replace `onExport` stub with real `fetch POST`.
4. Everything else — SVG chrome, neuron rendering, sidebar interaction, timeline scrubbing — stays byte-identical to what came out of Claude Design.

**Total wire surface:** 2 fetch calls. The Design work and the wiring work are cleanly separated.

---

## Why this is the right shape

- **Reliability:** backend is deterministic Python (hypotheses, graph signals). Frontend is deterministic React rendering a JSON contract. No LLM in the render path.
- **Simplicity:** one JSON contract (`brain_state.json`) is the only thing both halves agree on. Versioned independently.
- **Shareability:** the Aggregated export is a screenshot-worthy artifact — "here is what my AI-collaboration cortex looks like right now." Viral-shaped.
- **Compounds with use:** more sessions → denser neurons → sharper hypotheses. The viz is the visible *proof* that OmniGraph's substrate is growing.

---

## Open questions

1. **Anatomical accuracy.** Medically correct lateral brain view vs stylized / friendly illustration? My lean: stylized-correct (recognizable as a brain, not a medical reference) — Claude Design handles this well.
2. **Hypothesis evidence threshold.** Below what N does a hypothesis render as "insufficient data"? My lean: N=10 data points per hypothesis; below that, show a grey pill "needs more sessions" rather than a false verdict.
3. **Private-by-default vs discoverable-by-default.** Ship Aggregated as public-friendly default? My lean: yes — and a prominent "This is a sanitized view; full view is local-only" banner.
4. **Timeline scope.** Whole history (possibly months) vs last-30-days window? My lean: last-30-days default, toggle to whole history.
