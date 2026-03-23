"""
The Three Patterns — Annotated Reference
=========================================
This file is NOT meant to be run. It's a teaching reference that
shows each pattern in isolation with academic commentary.

Use this alongside 1_run_me.py to explain WHY each decision was made.
"""

# ============================================================
#
#  PATTERN 1 — SCHEMA-DRIVEN OUTPUT
#
#  Problem:  AI returns different shapes. Your parser breaks.
#  Solution: Force the model to call a tool with a strict schema.
#            The response is ALWAYS in block.input — a Python dict.
#            No json.loads. No regex. No "sometimes it wraps in markdown".
#
# ============================================================

SCHEMA_PATTERN = {
    # Define the shape ONCE as a tool input_schema
    "name": "your_tool_name",
    "description": "What to extract. ALWAYS say: 'You MUST call this tool.'",
    "input_schema": {
        "type": "object",
        "properties": {
            "field_name": {
                "type": "string",          # or integer, boolean, array
                "enum": ["a", "b", "c"],   # use enum to restrict valid values
                "description": "Be specific — the model uses this to fill the field correctly",
            },
        },
        "required": ["field_name"],        # always list every field you need
    },
}

# In your API call:
#   tools=[SCHEMA_PATTERN],
#   tool_choice={"type": "tool", "name": "your_tool_name"}   ← forces the call
#
# To read the result:
#   for block in response.content:
#       if block.type == "tool_use":
#           result = block.input   ← already a Python dict, guaranteed shape


# ============================================================
#
#  PATTERN 2 — MULTI-STEP DELEGATION
#
#  Problem:  One prompt trying to do everything → shallow output.
#  Solution: Each step has ONE job. Later steps receive clean input
#            from earlier steps — so they can go deeper.
#
#  The key insight: a model analysing clean structured data
#  produces better analysis than a model analysing raw messy text,
#  because it doesn't have to split attention between reading and thinking.
#
# ============================================================

# STEP 1 — EXTRACT (read the world, produce clean data)
#   Input : raw, unstructured text
#   Output: structured JSON (use Schema pattern here)
#   Rule  : NO analysis, NO opinions — just extraction

# STEP 2 — ANALYSE (think about the clean data)
#   Input : structured output from step 1
#   Output: judgements, scores, classifications (use Schema pattern here too)
#   Rule  : NO writing — just analysis

# STEP 3 — WRITE (communicate the analysis)
#   Input : structured extraction + analysis from steps 1 and 2
#   Output: human-readable text
#   Rule  : NO re-reading the raw source — trust the earlier steps

# Why this works:
#   Single-shot: model reads messy text AND analyses AND writes simultaneously
#                → context is split three ways → mediocre at all three
#
#   Multi-step:  each model call is an expert at exactly one thing
#                → each step is as good as it can possibly be
#                → errors are isolated (you can debug step 2 without touching step 1)


# ============================================================
#
#  PATTERN 3 — ROLE-BASED SYSTEM PROMPT
#
#  Problem:  No system prompt = the AI improvises tone, policy, and behaviour
#            differently every time.
#  Solution: Three explicit layers that remove all ambiguity.
#
# ============================================================

ROLE_TEMPLATE = """
## IDENTITY
You are [Name], a [specific role] at [Company].
You are [3 adjectives that define tone].
You [one sentence on communication style].

## CONSTRAINTS
You MUST:
- [Specific required behaviour 1]
- [Specific required behaviour 2]

You MUST NOT:
- [Specific forbidden behaviour 1]
- [Specific forbidden behaviour 2]

## CONTEXT
[Fact 1]: [Value — be precise, not vague]
[Fact 2]: [Value]
[Fact 3]: [Value]
"""

# Why three layers?
#
#   IDENTITY   → answers "who am I?" — anchors tone and ownership
#   CONSTRAINTS → answers "what are my rules?" — prevents policy invention
#   CONTEXT    → answers "what do I know?" — replaces guessing with facts
#
# Without IDENTITY:    tone varies wildly per conversation
# Without CONSTRAINTS: model invents plausible-sounding policies
# Without CONTEXT:     model fills knowledge gaps with hallucinations
#
# All three together = consistent, reliable, auditable behaviour


# ============================================================
#
#  HOW THEY COMBINE
#
#  Schema     ensures the pipeline never crashes at the seams
#             (step 1 output is always valid input for step 2)
#
#  Delegation ensures each step produces the highest quality output
#             it can, given its single responsibility
#
#  Role       ensures every step behaves the same way every time —
#             same labels, same tone, same decision rules
#
#  Without Schema:     delegation pipeline breaks unpredictably
#  Without Delegation: role-based single prompt hits quality ceiling
#  Without Role:       extraction and analysis are inconsistent across runs
#
#  The patterns are not optional add-ons — they solve different problems
#  and they compound each other's benefits.
#
# ============================================================
