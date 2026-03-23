"""
End-to-End Bug Triage System
============================
A complete AI feature that combines all three production patterns:

  Pattern 1 — SCHEMA      : Structured output via tool_use
                             Raw bug report  →  guaranteed JSON fields
                             (no more KeyError crashes at 3am)

  Pattern 2 — DELEGATION  : Three specialised steps in sequence
                             Extract  →  Analyse  →  Write
                             (each step has one job; quality compounds)

  Pattern 3 — ROLE        : Identity + Constraints + Context in every call
                             Every ticket looks the same, uses the same labels,
                             follows the same rules  (no more "creative" AI)

RUN:
    export OPENAI_API_KEY=your_key_here
    python 1_run_me.py
"""

import json
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()


# ============================================================
# PATTERN 3 — ROLE
# Three-layer system prompt used by every step in the pipeline.
# ============================================================

TRIAGE_AGENT_ROLE = """
## IDENTITY
You are Triage-Bot, a senior software engineer specialising in bug
classification at a B2B SaaS company. You are precise, concise, and
consistent. You never speculate beyond what the report contains.

## CONSTRAINTS
You MUST:
- Use only the severity labels: critical / high / medium / low
- Use only the priority labels: P0 / P1 / P2 / P3
- Base severity on user impact, not on the reporter's emotional language
- Set P0 only when production is down or data loss is occurring

You MUST NOT:
- Invent reproduction steps not mentioned in the report
- Assign owners or sprint dates
- Use phrases like "I think" or "possibly" — be definitive or say unknown

## CONTEXT
Severity guide:
  critical  →  data loss, security breach, or full outage
  high      →  core feature broken for a segment of users
  medium    →  degraded experience, workaround exists
  low       →  cosmetic, edge case, or minor inconvenience

Priority mapping (default):
  critical  →  P0   |   high  →  P1   |   medium  →  P2   |   low  →  P3
"""


# ============================================================
# PATTERN 1 — SCHEMA
# The extraction tool guarantees these fields always exist.
# ============================================================

EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_extracted_bug",
        "description": "Submit the structured data extracted from the raw bug report. You MUST call this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "title":        {"type": "string",  "description": "Short bug title (max 80 chars)"},
                "component":    {"type": "string",  "description": "Affected component or service"},
                "environment":  {"type": "string",  "description": "Where it happens: production/staging/local/unknown"},
                "steps":        {"type": "array",   "items": {"type": "string"}, "description": "Reproduction steps as a list"},
                "actual":       {"type": "string",  "description": "What actually happens"},
                "expected":     {"type": "string",  "description": "What should happen instead"},
                "affects_data": {"type": "boolean", "description": "Does this cause data loss or corruption?"},
            },
            "required": ["title", "component", "environment", "steps", "actual", "expected", "affects_data"],
        },
    },
}


# ============================================================
# PATTERN 2 — DELEGATION
# Three focused steps. Each one has a single responsibility.
# ============================================================

def step1_extract(raw_report: str) -> dict:
    """
    STEP 1 — Extract
    Job: read unstructured text, output guaranteed JSON fields.
    Uses the SCHEMA tool to enforce structure.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_extracted_bug"}},
        messages=[
            {"role": "system", "content": TRIAGE_AGENT_ROLE},
            {"role": "user", "content": f"Extract structured data from this bug report:\n\n{raw_report}"},
        ],
    )
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_extracted_bug":
                return json.loads(tool_call.function.arguments)
    raise RuntimeError("Extraction tool was not called")


def step2_analyse(extracted: dict) -> dict:
    """
    STEP 2 — Analyse
    Job: take clean structured data from step 1 and assign severity/priority/fix approach.
    It never re-reads the raw report — the extraction already did that cleanly.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=512,
        tools=[{
            "type": "function",
            "function": {
                "name": "submit_analysis",
                "description": "Submit the bug analysis. You MUST call this tool.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "severity":      {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "priority":      {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                        "category":      {"type": "string", "enum": ["crash", "data-loss", "performance", "ui", "auth", "integration", "other"]},
                        "fix_approach":  {"type": "string", "description": "One-sentence description of the fix direction"},
                        "needs_hotfix":  {"type": "boolean", "description": "Should this bypass the normal sprint cycle?"},
                    },
                    "required": ["severity", "priority", "category", "fix_approach", "needs_hotfix"],
                },
            },
        }],
        tool_choice={"type": "function", "function": {"name": "submit_analysis"}},
        messages=[
            {"role": "system", "content": TRIAGE_AGENT_ROLE},
            {"role": "user", "content": f"Analyse this extracted bug data:\n\n{extracted}"},
        ],
    )
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_analysis":
                return json.loads(tool_call.function.arguments)
    raise RuntimeError("Analysis tool was not called")


def step3_write_ticket(extracted: dict, analysis: dict) -> str:
    """
    STEP 3 — Write
    Job: take the structured extraction + analysis and produce a formatted ticket.
    By this point, all the hard thinking is done — this step just formats.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=600,
        messages=[
            {"role": "system", "content": TRIAGE_AGENT_ROLE},
            {
                "role": "user",
                "content": (
                    f"Write a Jira-style bug ticket using this data.\n\n"
                    f"Extracted fields: {extracted}\n\n"
                    f"Analysis: {analysis}\n\n"
                    f"Format:\n"
                    f"[PRIORITY] TITLE\n"
                    f"Severity : ...\n"
                    f"Component: ...\n"
                    f"Category : ...\n\n"
                    f"Steps to Reproduce:\n...\n\n"
                    f"Actual Behaviour: ...\n"
                    f"Expected Behaviour: ...\n\n"
                    f"Fix Approach: ...\n"
                    f"Hotfix Required: yes / no"
                ),
            },
        ],
    )
    return response.choices[0].message.content


# ============================================================
# ORCHESTRATOR — chains the three steps
# ============================================================

def triage_bug_report(raw_report: str) -> str:
    print("  [1/3] Extracting structured fields …")
    extracted = step1_extract(raw_report)

    print("  [2/3] Analysing severity and priority …")
    analysis = step2_analyse(extracted)

    print("  [3/3] Writing the ticket …")
    ticket = step3_write_ticket(extracted, analysis)

    return ticket


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    raw_report = """
    hey team, so ive been trying to export my data for the past two days and it just
    doesnt work??? i click export, it spins for like 30 seconds then just says
    "export failed" with no error message. im on the enterprise plan and i NEED this
    data for a board presentation on friday. this is really urgent!!

    i tried in chrome and safari, same thing. also tried with a smaller date range
    (last 30 days instead of last year) and THAT worked fine. so its definitely
    something with large exports. please fix asap
    """

    print("=" * 60)
    print("BUG TRIAGE SYSTEM — End-to-End Demo")
    print("=" * 60)
    print("\nRaw report (messy, emotional, unstructured):")
    print(raw_report)
    print("-" * 60)
    print("\nRunning three-step pipeline:\n")

    ticket = triage_bug_report(raw_report)

    print("\n" + "=" * 60)
    print("GENERATED TICKET:")
    print("=" * 60)
    print(ticket)
    print()
    print("Patterns used:")
    print("  Schema     → guaranteed fields in steps 1 and 2 (no crashes)")
    print("  Delegation → extract → analyse → write (quality compounds)")
    print("  Role       → same severity labels and tone every single time")
