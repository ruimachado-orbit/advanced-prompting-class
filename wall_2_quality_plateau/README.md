# Wall 2: Quality Plateau

## The Problem

A single prompt that asks the model to simultaneously read raw data,
extract themes, analyse them, and write polished prose will always
produce mediocre output. The model is context-switching between four
different cognitive modes — and it can't be an expert extractor,
analyst, and writer all at once.

The result is technically correct but painfully generic: "fix performance
issues", "improve documentation", "add more integrations". Any PM could
have written the same thing without reading the feedback.

## The Progression

### 1. `single_shot.py` — The ceiling you hit
One mega-prompt. One shallow output. The `SAMPLE_BAD_OUTPUT` constant
shows exactly what you get: named themes with no quantification, vague
recommendations with no specificity, an "executive summary" that could
describe any software product ever built.

### 2. `multi_step_delegation.py` — Break the ceiling
Three sequential steps, each with a focused system prompt:

| Step | Role | Input | Output |
|------|------|-------|--------|
| 1 — Extract | Data extraction specialist | Raw feedback | Structured themes JSON |
| 2 — Analyse | Senior product analyst | Themes JSON | Severity, churn risk, revenue impact |
| 3 — Synthesise | Exec communication specialist | Analysis JSON | Specific, data-backed summary |

Each step receives grounded data from the previous step, so no step
needs to hallucinate context. The final summary cites actual numbers
and names specific next actions.

### 3. `parallel_delegation.py` — Scale without waiting
When analysis steps are independent, run them simultaneously.
Three specialist calls (UX, Performance, Features) fire in parallel
via `ThreadPoolExecutor`. A fourth merge step combines them after all
three complete.

**Speedup: ~12s sequential → ~4-5s parallel (3x faster)**

## Key Takeaway

One prompt, one cognitive mode. If your task has multiple phases
(extract → analyse → synthesise, or UX → perf → features), use
multiple model calls. Quality and speed both improve.
