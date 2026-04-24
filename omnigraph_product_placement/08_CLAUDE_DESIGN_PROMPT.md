# Claude Design — paste-ready prompt

_Paste the block below into Claude Desktop with Claude Design active. It produces one Artifact: the full brain viz with mocked data, all 10 hypothesis overlays, timeline scrubber, and export dialog. Iterate by asking Claude to refine specific regions or components after._

---

## Prompt (paste this)

**Attach the reference image `ReferenceImage.webp` to the message alongside this prompt.** The visual fidelity target is that image: a high-fidelity, particle-system, animated neural render — thousands of glowing points forming an anatomical brain silhouette with colored fiber tracts radiating through it. Dense. Luminous. In constant motion. Think "scientific visualization of a connectome" rather than "diagram with labeled regions."

Build me a single React Artifact: an **interactive, high-fidelity, continuously animated application** — not a website, not a landing page, not a marketing page, not a documentation page, not a schematic diagram. This is a **running tool** that will be embedded inside another application (Atelier) via iframe. The entire viewport IS the tool's UI. There is no hero section, no nav bar, no footer, no "about" text, no feature list, no call-to-action buttons, no sign-up form, no testimonials, no marketing copy anywhere. Every pixel is the tool doing its job.

**Fidelity target — match the attached reference image:**
- Thousands of particles (3,000 – 8,000) forming the anatomical brain silhouette in left-lateral view.
- Rich rainbow palette: cool outer tracery (cyan / teal / emerald), warm mid-depth clusters (amber / yellow / orange), hot central cores (magenta / crimson / coral). Not a 4-color ramp — a full spectrum.
- Glowing points with additive blending; bloom/glow post-processing so bright clusters bleed into neighbors.
- Fiber tracts: thin curved filament lines radiating through the particle cloud, colored with per-fiber gradients (one end cool, other end warm), also additively blended.
- Dark teal / slate-950 background with a soft radial vignette toward edges.
- **Constant idle animation** — particles drift on noise-field micro-motion (never static), filaments shimmer (opacity + slight displacement), the whole brain "breathes" (1-2% scale oscillation, ~5s period). Even when no user interaction is happening, the scene is alive.
- Hypothesis overlays are **color/intensity modulations on top of the living base render** — they do not replace it. When a hypothesis activates, the relevant region's particles brighten / shift hue / pulse harder; unrelated regions dim slightly.

**Tech stack — use React Three Fiber, not SVG:**
- `@react-three/fiber` for the Three.js canvas.
- `@react-three/drei` for helpers (`OrbitControls` disabled — this is a fixed camera view; `EffectComposer` + `Bloom` for glow).
- `@react-three/postprocessing` for bloom + chromatic aberration (very subtle).
- Particles: one `InstancedMesh` of small sphere geometry with a custom `PointsMaterial` / `ShaderMaterial` doing additive blending + size-attenuation. Positions are precomputed from the brain silhouette.
- Fiber tracts: `<Line>` instances from drei, or custom `BufferGeometry` with `LineBasicMaterial` (`blending: AdditiveBlending`, `transparent: true`).
- Camera: fixed `PerspectiveCamera`, slight parallax on mouse move (±2° yaw/pitch) so the brain feels volumetric.
- SVG is fine ONLY for the UI chrome (hypothesis pills, verdict card, timeline, export dialog) — never for the brain itself.

**Brain silhouette source:** generate particle positions procedurally by sampling points inside a left-lateral brain shape. Approach: define 8 region ellipsoids in 3D (coordinates given below as `REGION_ANATOMY`); sample points inside each with Poisson-disk-like jitter; tag each point with its region id. This gives both the shape AND the region membership for hypothesis overlays in one pass.

**What to build:** an anatomical wireframe brain visualization of a founder's cognitive-computational activity with AI tools. It is a diagnostic mirror — regions of the brain map to types of thinking; data modulates firing; the viewer inspects hypotheses about their own patterns.

**What this is NOT (important — last time you interpreted a similar brief as a marketing site; do not do that):**
- Not a page that *describes* a brain viz tool.
- Not a page with a header that says "Brain Viz" and sections like "Features / How it works / Get started".
- Not a product landing page.
- Not a documentation site with copy blocks.
- If your output contains any `<section>` with prose paragraphs describing capabilities, you have misunderstood. Delete it. The app speaks for itself by running.

**Embeddability constraints (this is iframe'd into Atelier):**
- Mount full-viewport: the root container is `h-screen w-screen overflow-hidden` (or `h-full w-full` if the iframe controls sizing). No page margin, no centered max-width content column.
- No external fonts that require network fetches — use system font stack or Tailwind's built-in `font-sans` / `font-mono` fallbacks.
- No fixed/sticky elements anchored to the viewport in a way that breaks when iframe is resized — use flex/grid layout that adapts.
- Do not assume a window larger than 900×600. Design for that as a lower bound; scale up gracefully.
- Emit a `postMessage` stub when a hypothesis is activated or an export is requested, so the parent (Atelier) can react: `window.parent.postMessage({type: 'brainviz:hypothesis', id}, '*')` — add a comment `// WIRE POINT: parent origin should be checked in production`.

**Design system to use:**

- Background: deep teal-slate (`#0a1824` to `#0f172a`), with a soft radial vignette darkening the corners.
- Brain chrome: no hard outlines — the silhouette emerges from the particle density itself (reference image style). Optional extremely faint (opacity 0.05) outline stroke only as a guide during particle generation, removed at render.
- Particle palette (full spectrum, per region):
  - Prefrontal: amber / gold (`#fbbf24`, `#f59e0b`)
  - Motor: coral / crimson (`#fb7185`, `#f43f5e`)
  - Hippocampus: emerald / teal (`#10b981`, `#14b8a6`)
  - Amygdala: magenta / hot-pink (`#e879f9`, `#ec4899`)
  - Brainstem: cyan / sky (`#22d3ee`, `#38bdf8`)
  - Sensory: yellow / lime (`#facc15`, `#a3e635`)
  - Anterior cingulate: orange / red (`#fb923c`, `#ef4444`)
  - Corpus callosum: violet / indigo (`#a78bfa`, `#818cf8`)
  Each region's particles use its palette with per-particle hue jitter (±15°) to get the organic rainbow look of the reference.
- Particle size: 0.02 – 0.08 world units, size-attenuated by distance, with additive blending so overlaps bloom naturally.
- Fiber tracts: thin curved lines (0.5–1.5px rendered, opacity 0.3–0.9), colored by a per-fiber gradient between two region palettes. Active hypothesis fibers animate a flowing "dash" (shader-driven moving offset along the curve).
- UI chrome (pills, verdict card, timeline, export): glass panel (`bg-white/5 backdrop-blur-md border border-white/10 rounded-xl`), typography Inter (sans) + JetBrains Mono (mono). Pills are small rounded-full `bg-white/5` when inactive, region-accent-colored (from the palette above, ~20% opacity fill + matching text) when active. Insufficient-data pills show a grey dot indicator.
- Verdict card: glass panel (bg-white/5, backdrop-blur-md, border border-white/10, rounded-xl, p-5). One large numeral or short phrase, one-line verdict below in mono.
- Typography: `font-sans` Inter-style for labels/controls, `font-mono` JetBrains-style for verdict numerals and timestamps. Two weights: 400 and 600.
- Hypothesis pills: small rounded-full, bg-white/5 when inactive, bg-violet-500/20 with violet-300 text when active. Shortened label + a dot indicator when the hypothesis has "insufficient data".

**Layout:**

- Full-viewport. Center: the brain SVG (side profile, left-facing, ~600px tall). Left rail (256px): 10 hypothesis pills stacked, grouped into 4 sections (Collaboration-health, Cognitive-load, Cross-project, Tool-fit). Right rail (320px): verdict card for the topmost active hypothesis + top-3 evidence list. Bottom (80px): horizontal timeline scrubber with play/pause and speed (1x / 4x / 16x). Top-right corner: a small "Export" button that opens a modal with three radio options (None / Named-entities-stripped / Aggregated-only).

**Brain regions — 3D ellipsoid anatomy (`REGION_ANATOMY` constant at top of file):**

Generate a JS constant defining 8 region ellipsoids in left-lateral view (camera looking down -X, brain facing -Z). Left-front is (-x, 0, -z); rear is (+x... no wait, correct orientation: front is +X, top is +Y, the brain faces +X). Use these approximate centers and radii (world units, brain roughly 4 wide × 3 tall × 2 deep):

```js
const REGION_ANATOMY = {
  prefrontal:          { center: [ 1.4,  0.6,  0.0], radii: [0.8, 0.7, 0.9], label: "Planning",          particles: 900 },
  motor:               { center: [ 0.4,  1.1,  0.0], radii: [0.6, 0.4, 0.8], label: "Execution",         particles: 500 },
  sensory:             { center: [-0.4,  1.0,  0.0], radii: [0.6, 0.4, 0.8], label: "Inputs",            particles: 500 },
  anterior_cingulate:  { center: [ 0.9,  0.2,  0.0], radii: [0.5, 0.6, 0.4], label: "Concerns",          particles: 700 },
  hippocampus:         { center: [ 0.0, -0.3,  0.0], radii: [0.4, 0.3, 0.5], label: "Memory",            particles: 450 },
  amygdala:            { center: [ 0.3, -0.6,  0.0], radii: [0.3, 0.3, 0.4], label: "Affect",            particles: 350 },
  brainstem:           { center: [-0.6, -0.9,  0.0], radii: [0.3, 0.6, 0.3], label: "Tools",             particles: 600 },
  corpus_callosum:     { center: [ 0.0,  0.3,  0.0], radii: [1.2, 0.15, 0.3],label: "Cross-pollination", particles: 400 },
};
```

For each region, sample `particles` count of points uniformly inside the ellipsoid with 3D jitter. Tag each point with `{region_id, color: hueJitter(regionPalette[region_id], ±15)}`. Total ≈ 4,400 particles.

Draw ~30 fiber tracts as cubic Bézier curves connecting pairs of regions (prefrontal↔motor, prefrontal↔anterior_cingulate, corpus_callosum↔all, etc. — hand-author the connection list). Each fiber's curve is sampled to ~80 points for smoothness; endpoints offset slightly into the region volume so fibers look embedded, not stuck-on.

Labels: small text tags (Inter 11px, zinc-400, opacity 0.7) drawn as HTML overlay via drei's `<Html>` — anchor to each region's center, offset outward by ~1.5× the region's outer radius. Only show labels for the active hypothesis's regions; fade others to opacity 0.

**Data shape the component consumes (put this as a TypeScript interface at the top):**

Particles and fibers are client-generated from `REGION_ANATOMY`. The server sends per-region aggregates, hypothesis overlays, and a temporal event stream — not 4,400 point coordinates. This keeps the payload small (<100KB) and the render smooth.

```ts
interface BrainState {
  regions: Array<{
    id: 'prefrontal' | 'motor' | 'hippocampus' | 'amygdala' | 'brainstem' | 'sensory' | 'anterior_cingulate' | 'corpus_callosum';
    density: number;         // 0..1 — multiplies base particle brightness
    color_temp: number;      // -1 (cool shift) .. 1 (warm shift) — hue rotation on region palette
    last_fired_ts: number;   // unix ms — drives pulse timing
  }>;
  fibers: Array<{
    from_region: string;
    to_region: string;
    weight: number;          // 0..1 — opacity + flow speed
    active: boolean;         // drives dashed-flow shader animation
  }>;
  hypotheses: Record<string, {
    id: string;
    label: string;
    group: 'collab' | 'cogload' | 'cross' | 'toolfit';
    firing_pattern: { region: string; intensity: number }[]; // intensity 0..1, blended onto base render
    verdict: string;         // one line
    top_evidence: { label: string; detail: string }[];
    sufficient_data: boolean;
  }>;
  timeline: Array<{ ts: number; fired_regions: string[] }>; // region-level events, not per-neuron
}
```

**Per-particle render (computed client-side, not stored in state):**
Each particle knows its `region_id` from generation time. On every frame:
- Base brightness = `regions[region_id].density` × noise-field flicker.
- Hue = `regionPalette[region_id]` + `jitter` + `regions[region_id].color_temp × 30°`.
- Additive boost = sum over active hypotheses of `firing_pattern[region_id].intensity × pulse(t)`.
- Micro-motion = particle's original position + 0.02 × simplex3D(pos, t×0.15) — always on.

This is the animation core. The scene is never still.

**Generate mock data inline as a constant `MOCK_BRAIN_STATE` at the top of the file.** Include:

- All 8 regions with varied density/color_temp.
- ~40 neurons distributed across regions (more in prefrontal, anterior_cingulate, brainstem; fewer in corpus_callosum).
- ~60 synapses, 10 of which are cross_region (violet).
- All 10 hypotheses keyed by these ids, with plausible verdicts:
  1. `rehearsal_vs_commitment` (collab) — "Many decisions re-open within 2 sessions."
  2. `concern_debt` (collab) — "3 concerns open for >14 days."
  3. `affect_before_abandonment` (collab) — "Amygdala pattern matches prior abandonment signature."
  4. `drift_by_session_time` (cogload) — "Evening drift rate is 2.3× morning."
  5. `concurrent_project_pressure` (cogload) — "Above-3 projects/week correlates with 40% higher drift."
  6. `tool_storm` (cogload) — "Top 10% tool-storm sessions produce 30% of concerns."
  7. `cross_pollination_vs_bleed` (cross) — "4 cross-project fibers are productive; 2 are leaky."
  8. `provider_specific_cognition` (cross) — "You raise 3× more concerns on Antigravity; ship 2× faster on Claude Code."
  9. `rule_firing_under_pressure` (toolfit) — "Simplicity-first fires 4× more in morning sessions."
  10. `silent_failure` (toolfit) — "5 decisions rest on now-deprecated premises."

Give two of them `sufficient_data: false` so the insufficient-data indicator can be seen.

- `timeline` ~30 entries spanning the last 30 days.

**Interactions:**

- Clicking a hypothesis pill toggles it active. Allow up to 3 active at once; when multiple active, blend their `firing_pattern` into the region rendering (additive intensity, clamped to 1).
- Verdict card shows the **top-most active** hypothesis (first in rail order among active).
- Timeline scrubber: dragging the handle sets `currentTime`. Neurons whose `last_fired_ts` is within a 1-hour window of `currentTime` render at full opacity + pulsing; others fade to 0.3 opacity. Play button animates currentTime forward at the selected speed.
- Export button opens a dialog with three radios + a "Export" action. Dialog's action logs `{level}` to console for now.

**State management:** single `useState` for `{activeHypotheses: string[], currentTime: number, playing: boolean, speed: number, exportOpen: boolean}`. No external state library.

**Data source:** put ALL data fetching behind a single hook `useBrainState()` that currently returns `MOCK_BRAIN_STATE`. Add a comment: `// WIRE POINT: replace body with fetch('http://localhost:8787/brain/state').then(r => r.json())`.

**Export handler:** `onExport(level)` currently logs to console. Add a comment: `// WIRE POINT: replace with fetch('http://localhost:8787/brain/export', { method: 'POST', body: JSON.stringify({level}) })`.

**Tone:** the visual should feel like an observatory — calm, dark, precise. Not a dashboard. The user should feel they are looking at an organ, not a chart.

Render the brain SVG first-pass anatomically recognizable but stylized; I will refine regions in follow-up prompts.

---

## Follow-up prompts (use after the first Artifact lands)

After the initial Artifact is generated, iterate with these:

1. **"Refine the prefrontal cortex outline — it should curl forward more and be larger relative to motor; move the 'Planning' label further out to the left."**
2. **"The synapses are too dense near hippocampus — reduce their opacity baseline to 0.05, and only let the top-20-weight ones render above 0.3 opacity."**
3. **"When two hypotheses are both active, currently the verdict card only shows the top one — add a tiny 'stacked with N others' indicator below the verdict."**
4. **"Add a subtle breathing animation to the whole brain outline (1% scale oscillation, 4s period) that pauses when any hypothesis is active."**
5. **"The timeline is too bright — make the unscrubbed portion zinc-800 and the scrubbed-through portion a soft violet gradient."**
6. **"Add keyboard shortcuts: 1-0 toggles hypotheses by group-order; space plays/pauses; E opens export."**

Each of these is a small iteration Claude Design can handle in one turn without rebuilding.
