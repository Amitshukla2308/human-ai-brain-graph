# OmniGraph 🧠

**OmniGraph** is a persistent, bi-directional Knowledge Graph and Meta-Learning repository generated autonomously from historical AI conversations. 

Every time you interact with an AI, you generate raw intellectual capital (code, architectural decisions, debugging methodologies, and behavioral patterns). OmniGraph is an ETL (Extract, Transform, Load) pipeline that harvests this raw history and compiles it into a centralized "Brain" that future AI agents can natively read.

## ✨ The Core Philosophy (Why we are building this)

When you open a new AI chat, the AI has **amnesia**. It doesn't know who you are, what projects you've abandoned, what your coding style is, or how your historical architectures function. 

OmniGraph solves this by splitting your history into two actionable databases:
1. **The Vault (The What)**: A network of MarkDown files capturing every software entity, script, and architecture you've ever built, linked by the session they were created in.
2. **The Meta-Profile (The How & Who)**: An aggregated JSON profile tracking your developer habits, your bottlenecks, and the historical failure patterns of the AIs you've used.

---

## 🗺️ Project Roadmap & Deliverables

### Phase 1: The Scaffolding & Pilot Extraction (✅ We are here)
**Objective**: Build a resilient LLM pipeline capable of parsing ugly JSON/JSONL telemetry into structured data using local inference (Qwen3.6 35B).
*   **Deliverables**: 
    *   Unified `ai_conversations` archive (700+ conversations).
    *   `extractor.py` backend script using `json-repair` to guarantee structural integrity.
    *   Initial population of isolated Markdown nodes in `/vault`.

### Phase 2: The Meta-Brain Aggregation (Next Step)
**Objective**: Hook up the User and AI profiling logic to build the "Mutual Brain".
*   **Deliverables**:
    *   Update extractor to accurately dump `meta_learnings_user` and `meta_learnings_ai` across sessions.
    *   Build an aggregator script that compiles thousands of isolated meta-learnings into a single, deduplicated `global_profile.json`.

### Phase 3: The Wiki Graph (Sanitization & Linking)
**Objective**: Transform isolated Vault nodes into a true bi-directional graph.
*   **Deliverables**:
    *   Fix the URL/filename sanitization bugs (restoring `.ts` and `/` paths).
    *   Implement cross-linking (so if `Canvas.md` relies on `world.md`, the Markdown files physically link to each other).
    *   Scale the extractor to process all 700 conversations asynchronously.

### Phase 4: Agent Integration (The Output)
**Objective**: Make the Graph useful for your daily AI workflows.
*   **Deliverables**:
    *   A compiled `SYSTEM_PROMPT_INJECTION.md` built from `global_profile.json` that you can paste into Claude/Cursor/LM Studio.
    *   A semantic vector search script (optional) allowing AI agents to query the `/vault` directly for context before giving you an answer.

---

## ⚙️ Technical Implementation Plan

To achieve the phases above, the OmniGraph pipeline relies on the following local stack:
*   **Hardware Extraction Engine**: RTX 5090 (31.5 GB VRAM) running `Qwen3.6-35B-A3B` via LM Studio (bound to `0.0.0.0:1234`).
*   **Prompt Architecture**: Enforcing a strict Pydantic-like JSON schema in the System Prompt for bulletproof local inference.
*   **Parsing Layer**: Using `json-repair` in Python to dynamically deserialize hallucinated or malformed JSON responses from the 35B model.

### 1. The Meta-Brain Architecture
Instead of tracking individual concepts ad-hoc, we will track continuous arrays.
**The Aggregator Flow**:
1. `extractor.py` queries Qwen.
2. Qwen outputs `{"meta_learnings_user": ["Prefers Python type hints"], "meta_learnings_ai": ["Tool X failed on Y"]}`.
3. The extractor loads `global_profile.json`, appends the new lists, and completely deduplicates identical conceptual learnings using either a text differential or a lightweight semantic filter.

### 2. Graph Database vs. Flat Markdown
**Technical Choice**: We chose Bi-directional Markdown (Obsidian-style) over Neo4j.
**Why**: 
*   **AI Native**: Modern LLMs have immense sequence length context windows. They can natively ingest 100+ markdown files instantly.
*   **Human Readable**: Neo4j requires Cypher queries. Markdown requires just clicking the file. 
*   **Linking Logic**: We will enforce strict node titles. If an entity mentions "reflection-worker", the Python layer will regex search the vault for `reflection-worker.md` and wrap the text in standard `[[reflection-worker]]` brackets.

### 3. Scaling & Execution
Running 700 files serially through a 35B local model takes time. 
*   **Checkpointing**: We will write a lightweight `processed_sessions.log` cache. The script will check this file on startup so that if WSL crashes or you pause the engine, it resumes processing exactly where it left off without duplicating tokens.
*   **Batching**: We will process transcripts via single-shot asynchronous polling against the OpenAI-compatible LM Studio API.

---

## 🤖 How to Use It With Any AI Agent

Once OmniGraph is fully compiled (Phase 4), its applications are universal:

### Application 1: Context Injection (The System Prompt)
You will take the final `global_profile.json` output, convert it to a short text summary, and paste it directly into your AI Agent's "Custom Instructions" or System Prompt template.
**Example Impact**: The AI will instantly know to avoid Tailwind CSS if you prefer pure CSS, it will know not to abstract classes too much, and it will know exactly how you like your Docker configurations set up.

### Application 2: RAG / Workspace Anchoring
Tools like **Cursor**, **Claude Code**, or **Continue.dev** allow you to index local folders using `@folder` or Context embeddings.
By indexing the `/vault` directory, whenever you ask the AI to "Fix the reflection worker", the AI will read the `/vault/reflection-worker.md` file, see exactly when you built it, what its purpose was, and what other files it depends on, **saving you from having to re-explain the architecture.**

### Application 3: Self-Correction (For the AI)
Because OmniGraph tracks **AI Meta-Learnings** (e.g., "The model consistently failed when attempting complex regex parsing in session X"), the final system prompt actually warns the AI about its own historical weaknesses so it stops repeating past mistakes.
