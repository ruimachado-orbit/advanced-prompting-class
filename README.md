# Advanced Prompting — Three Walls, Three Patterns

A hands-on workshop that teaches three production prompting patterns by walking through the "walls" every team hits when shipping AI features — and the engineering patterns that break through them.

## The Three Walls

### Wall 1 — Inconsistent Outputs

The model returns different JSON shapes every time. Your parser assumes one structure, the model returns another, and your app crashes in production.

| Script | What it shows |
|--------|---------------|
| `1_broken_version.py` | The problem: three plausible outputs that all break a naive parser |
| `2_schema_version.py` | The fix: force structured output via `tool_use` schemas |
| `3_with_validation_and_fallback.py` | Production hardening: validation, retry logic, and safe fallbacks |
| `4_pydantic_validation.py` | Pydantic as a contract between AI output and application code |

### Wall 2 — Quality Plateau

One mega-prompt trying to do everything at once produces shallow, generic output.

| Script | What it shows |
|--------|---------------|
| `1_single_shot.py` | The problem: a single prompt that produces surface-level analysis |
| `2_multi_step_delegation.py` | The fix: extract → analyse → synthesise (sequential pipeline) |
| `3_parallel_delegation.py` | Advanced: run independent analysis steps concurrently, then merge |

### Wall 3 — Consistency Crisis

A vague system prompt lets the model improvise tone, policy, and behavior differently every time.

| Script | What it shows |
|--------|---------------|
| `1_generic_assistant.py` | The problem: same question, three contradictory answers |
| `2_role_based_system.py` | The fix: Identity + Constraints + Context layers in the system prompt |
| `3_consistency_testing.py` | Measuring consistency programmatically with assertion-based scoring |

## End-to-End Bug Triage

A complete system that combines all three patterns into a real feature: raw bug reports go in, structured Jira-style tickets come out.

| File | Purpose |
|------|---------|
| `1_run_me.py` | CLI demo — runs the full extract → analyse → write pipeline |
| `2_the_patterns.py` | Annotated reference (not runnable) — explains each pattern in isolation |
| `gradio_ui/app.py` | Interactive web UI built with Gradio |

## Setup

```bash
# 1. Install dependencies
pip install openai python-dotenv pydantic gradio

# 2. Configure environment
cp .env.template .env
# Edit .env and add your OpenAI API key

# 3. (Optional) Change the model
# Edit OPENAI_MODEL in .env (defaults to gpt-4o)
```

## Running

Each script can be run directly:

```bash
python3 wall_1_inconsistent_outputs/1_broken_version.py
```

Or use the Makefile shortcuts:

```bash
make help      # Show all available targets
make 1_1       # Wall 1, example 1
make 2_2       # Wall 2, example 2
make 3_3       # Wall 3, example 3
make e2e_1     # End-to-end bug triage (CLI)
make app       # Launch the Gradio web UI
```

## Project Structure

```
.
├── wall_1_inconsistent_outputs/   # Schema-driven output pattern
├── wall_2_quality_plateau/        # Multi-step delegation pattern
├── wall_3_consistency_crisis/     # Role-based system prompt pattern
├── end_to_end_bug_triage/         # All three patterns combined
│   └── gradio_ui/                 # Interactive web demo
├── slides/                        # Presentation slides (PDF)
├── .env.template                  # Environment variable template
└── Makefile                       # Run shortcuts
```
