# Wall 1: Inconsistent Outputs

## The Problem

You ask Claude to return structured data. Sometimes you get clean JSON.
Sometimes you get prose. Sometimes you get JSON wrapped in markdown fences
with different field names. Any downstream code that assumes a fixed shape
will crash unpredictably — and silently in production.

## The Progression

### 1. `broken_version.py` — What goes wrong
A plain-text prompt asks for JSON. The model obliges, but uses whichever
field names and format felt natural at inference time. Three sample raw
outputs are shown, each of which breaks the naive `parse_review()` function
in a different way (JSON decode error, missing key, wrong key name).

### 2. `schema_version.py` — Enforce the contract
Use Claude's `tools` parameter with `tool_choice` set to your specific tool.
The model is now required to populate your exact `input_schema`. The
structured data arrives in `content[].input` — already a Python dict, no
`json.loads` needed, no field-name surprises.

**Result: 40% crash rate → 0% crash rate.**

### 3. `with_validation_and_fallback.py` — Production hardening
Schema enforcement stops format surprises, but the model can still return
in-range values that violate business rules (empty theme list, summary that
is one word, etc.). This file adds:

- `validate_output()` — checks types, ranges, and content quality.
- Retry loop — up to 3 attempts; each retry feeds the previous errors back
  to the model so it can self-correct with increasing specificity.
- `safe_parse_with_fallback()` — if all retries fail, returns a safe neutral
  default and logs the failure for human review instead of crashing.

## Key Takeaway

Plain-text prompts → inconsistent formats → runtime crashes.
Tool-use schema → guaranteed shape → predictable code → production confidence.
