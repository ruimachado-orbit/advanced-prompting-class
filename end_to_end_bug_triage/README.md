# End-to-End Example: Bug Triage System

A complete production-ready AI feature that combines all three patterns
from the masterclass into one coherent system.

## The scenario

An engineer pastes a raw bug report into your system. The system must:
1. Extract structured data from the report (any format, any length)
2. Analyse severity, assign priority, and suggest a fix approach
3. Produce a consistent, professional Jira-style ticket

## The three patterns — where each one appears

| Pattern | Where it's used | Why it's needed |
|---|---|---|
| **Schema** (Wall 1) | Step 1 — extraction | Bug reports arrive in any format; we need guaranteed fields |
| **Delegation** (Wall 2) | Steps 1→2→3 pipeline | Extraction, analysis, and writing are three different jobs |
| **Role** (Wall 3) | Every API call | Keeps tone, field names, and severity labels consistent |

## Files

```
1_run_me.py          ← START HERE — the full pipeline, one file, 120 lines
2_the_patterns.py    ← Annotated breakdown of each pattern in isolation
```

Run:
```bash
export ANTHROPIC_API_KEY=your_key
python 1_run_me.py
```
