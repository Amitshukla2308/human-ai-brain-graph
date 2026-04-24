# Methodology — narrow-first substrate, then projection

_Written 2026-04-24 after Amit explained why he deliberately withheld the Gemini-level broader ambition until omnigraph v0.2.1 and 208 extracted sessions were done._

_(The arc captured in this file — the worked example done ON omnigraph — is the **reference exemplar** for what Atelier will ship as the **Product Placement Flow**: a repeatable 6-phase founder thinking exercise offered at every new project boot. Skip option + deferrable to project settings. Per `README.md` layering declaration and `04_PROPOSED_BUILD_ORDER.md` Step 3.)_

## Amit's stated reasoning (direct quote)

> "I deliberately did this (I did not want you to have broader goal before building what we have). Reason — Without what we have built i.e. project scoped pipeline, we will skip the project bias from the meta-learning. I as amit would go deeper on a project that I want to actually ship vs a project that's just a hobby. So what I did as a human, I used gemini chat to discuss on broader level, to get what I need to get started, Used Antigravity to organise the conversations in a single folder and then came to you (executor) to reflect over the spilled beans and make a sugarless coffee out of it. Now that we have coffee, we decide how much sugar amit needs."

## The core insight — weight-preservation via ordering

**Project-scoped first, abstract later** is not conservatism. It preserves a signal that abstract-first would flatten.

The signal: **your engagement depth with a project is itself meta-learning.** Amit goes deep on projects he intends to ship (Fastbrick, Atelier) and brushes past hobbies. Sessions spent agonizing over Fastbrick's legal posture have different weight than sessions where he idly wondered about a hobby.

If you strip project names too early (the Gemini-style "concepts only" framing), you lose:
- Which decisions were rehearsed-then-revisited vs one-shot
- Which drifts recurred within the same project vs across projects
- Which mental moves fired when shipping-pressure was on vs off
- Who the founder IS when the stakes were real

**Abstract-first = weight-flattening.** A mental move observed under "I was agonizing about Fastbrick" carries more signal than the same move under "I was playing with a hobby idea." Strip the project, strip the pressure context, strip the signal.

**Project-scoped-first, then projection = weight-preserving.** Build the project-specific substrate; derive project-agnostic views as compressions that keep the weight information in aggregate statistics (mention-frequency-per-shipping-project, drift-rate-under-pressure, etc.).

## The three-role workflow Amit used

Pattern noticed, worth naming:

| Role | Agent | Purpose |
|---|---|---|
| Brainstorm partner | Gemini (chat) | Wide framing, cheap to argue with, safe-to-speculate |
| Organizer | Antigravity | Corral raw substrate into a curated location |
| Executor | Claude Opus (me) | Reflect, build the narrow concrete thing |
| Through-line holder | Amit | Sequencing authority — decides when each agent enters |

Each role is optimized for a different cognitive labor. None is asked to do all three. The founder holds orchestration authority.

This pattern generalizes — Atelier is arguably building exactly this orchestration as a product. The "Drafter / Implementor" split is a version of brainstorm/executor. What's missing in Atelier's current design is **the organizer role** and **the founder's sequencing authority made explicit**.

## "Sugarless coffee first, then sugar" — the projection metaphor

Amit's framing on 2026-04-24:

> "Now that we have coffee, we decide how much sugar amit needs."

- **Coffee = project-scoped Vault + Meta-Profile.** Bitter, concrete, weight-preserving. The narrow build.
- **Sugar = abstraction / anonymization / generalization.** Added on top for different consumers, never poured back into the pot.

Different sugar levels for different product surfaces:

| Sugar level | What's stripped | What's preserved | Who consumes it |
|---|---|---|---|
| **None (Vault as-is)** | nothing | project names, entities, evidence, chronology | Atelier-for-Amit, his personal agents, the prompt compiler for his own workflow |
| **Light** | project names → anonymized tokens | structural relationships, decision shape, drift patterns | Atelier-for-other-founders (share schema + patterns, not content) |
| **Medium** | entities removed entirely | mental moves, rules, drifts, affect patterns, concern-lifecycle pattern types | Exportable "developer personality" — travels between Amit's machines / employers / AI tools |
| **High** | even mental moves abstracted to category | disposition archetypes, frequency distributions, failure-mode taxonomies | Aggregate research, shared across many users, the "Codex" / population-level layer |

Each level is a **derived projection** of the level below. The Vault stays; higher sugar is a view, not a replacement. The compiler that generates each view can be run on-demand.

This resolves the Vault-vs-Codex question from `01_`: they aren't two products; they're two projections of the same substrate. Build the compilers separately.

## Applying the methodology going forward

### What to do when Amit gives a narrow scope

1. Build TO that scope. Do not speculatively expand to broader ambitions even when they seem implied.
2. After the narrow thing is built, ask: *"does this compose into a broader framing you've already thought about?"* That's the correct window for broader ambition to enter.
3. Treat the narrow brief as layer 0. Higher-sugar projections come later as explicit compile steps.

### What NOT to do

- When I feel the urge to generalize early ("this would be more powerful as an abstract schema") → stop. Ask whether the concrete weight-preserving version should exist first.
- When I feel the urge to propose v0.1 → v0.2 → v0.3 in the same session → stop. Lock the current level, iterate empirically before the next projection.

### What Amit's pattern reveals about founder-craft

Good founders use multi-agent workflows because no single agent is good at all three (brainstorm, organize, execute). The expensive human labor is **sequencing** — knowing which agent to bring in when, and when to withhold information from an agent to prevent premature abstraction.

Atelier's real product bet might be: **make this sequencing legible and configurable.** Let the founder declare "I'm in brainstorm mode" (verbose Drafter, wide stance) vs "I'm in organize mode" (Canvas curation, no new nodes) vs "I'm in execute mode" (Implementor only). The current Atelier design implies this but doesn't make it explicit as a mode.

## Saved as memory

Pattern written to `~/.claude/projects/-home-beast-projects-omnigraph/memory/amit_withholds_broad_ambition_deliberately.md` — load-bearing for future sessions.
