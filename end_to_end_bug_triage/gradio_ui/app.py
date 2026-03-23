"""
Bug Triage System — Gradio UI
==============================
Demonstrates all three patterns live:
  Pattern 1 — Schema     : structured extraction via tool_use
  Pattern 2 — Delegation : extract → analyse → write
  Pattern 3 — Role       : consistent labels and tone every time

Run:
    python app.py
"""

import json
import hashlib
import textwrap
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gradio as gr
from openai import OpenAI

client = OpenAI()

# ── Cache ─────────────────────────────────────────────────────────────────────
# Persists results to disk so repeated runs never hit the API again.

CACHE_FILE = Path(__file__).parent / ".cache.json"

def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}

def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()

_cache = _load_cache()

# ── Pattern 3: Role ──────────────────────────────────────────────────────────

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

# ── Pattern 1: Schema ────────────────────────────────────────────────────────

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

# ── Pattern 2: Delegation ────────────────────────────────────────────────────

def step1_extract(raw_report: str) -> dict:
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
                        "severity":     {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "priority":     {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                        "category":     {"type": "string", "enum": ["crash", "data-loss", "performance", "ui", "auth", "integration", "other"]},
                        "fix_approach": {"type": "string", "description": "One-sentence description of the fix direction"},
                        "needs_hotfix": {"type": "boolean", "description": "Should this bypass the normal sprint cycle?"},
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


# ── Orchestrator ─────────────────────────────────────────────────────────────

def clear_cache():
    global _cache
    _cache = {}
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    return "Cache cleared."


def triage(raw_report: str):
    if not raw_report.strip():
        yield None, None, "", ""
        return

    key = _cache_key(raw_report)
    if key in _cache:
        cached = _cache[key]
        yield json.loads(cached["extracted"]), json.loads(cached["analysis"]), cached["ticket"], "⚡ Served from cache"
        return

    yield None, None, "", "🔄 Step 1 — Extracting..."
    extracted = step1_extract(raw_report)
    extracted_str = json.dumps(extracted, indent=2)

    yield extracted, None, "", "🔄 Step 2 — Analysing..."
    analysis = step2_analyse(extracted)
    analysis_str = json.dumps(analysis, indent=2)

    yield extracted, analysis, "Writing ticket...", "🔄 Step 3 — Writing ticket..."
    ticket = step3_write_ticket(extracted, analysis)

    _cache[key] = {"extracted": extracted_str, "analysis": analysis_str, "ticket": ticket}
    _save_cache(_cache)

    yield extracted, analysis, ticket, "✅ Done — result cached"


# ── Code snippets for the "Show Code" panels ────────────────────────────────

STEP1_CODE = textwrap.dedent("""\
    # Pattern 1: Schema — Force structured output via tool/function calling
    # The model MUST fill in every field defined in the schema.

    EXTRACT_TOOL = {
        "type": "function",
        "function": {
            "name": "submit_extracted_bug",
            "description": "Submit the structured data extracted from the raw bug report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":        {"type": "string",  "description": "Short bug title (max 80 chars)"},
                    "component":    {"type": "string",  "description": "Affected component or service"},
                    "environment":  {"type": "string",  "description": "production/staging/local/unknown"},
                    "steps":        {"type": "array",   "items": {"type": "string"}},
                    "actual":       {"type": "string",  "description": "What actually happens"},
                    "expected":     {"type": "string",  "description": "What should happen instead"},
                    "affects_data": {"type": "boolean", "description": "Data loss or corruption?"},
                },
                "required": ["title", "component", "environment", "steps",
                             "actual", "expected", "affects_data"],
            },
        },
    }

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "function",
                     "function": {"name": "submit_extracted_bug"}},
        messages=[
            {"role": "system", "content": TRIAGE_AGENT_ROLE},
            {"role": "user",   "content": f"Extract structured data from this bug report:\\n\\n{raw_report}"},
        ],
    )

    # Result is always in tool_calls — guaranteed by tool_choice
    tool_call = response.choices[0].message.tool_calls[0]
    extracted = json.loads(tool_call.function.arguments)
""")

STEP2_CODE = textwrap.dedent("""\
    # Pattern 2: Delegation — Each step has ONE job.
    # Step 2 receives clean data from Step 1 and focuses only on analysis.

    ANALYSIS_TOOL = {
        "type": "function",
        "function": {
            "name": "submit_analysis",
            "description": "Submit the bug analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity":     {"type": "string", "enum": ["critical","high","medium","low"]},
                    "priority":     {"type": "string", "enum": ["P0","P1","P2","P3"]},
                    "category":     {"type": "string", "enum": ["crash","data-loss","performance",
                                                                 "ui","auth","integration","other"]},
                    "fix_approach": {"type": "string"},
                    "needs_hotfix": {"type": "boolean"},
                },
                "required": ["severity","priority","category","fix_approach","needs_hotfix"],
            },
        },
    }

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=512,
        tools=[ANALYSIS_TOOL],
        tool_choice={"type": "function",
                     "function": {"name": "submit_analysis"}},
        messages=[
            {"role": "system", "content": TRIAGE_AGENT_ROLE},
            {"role": "user",   "content": f"Analyse this extracted bug data:\\n\\n{extracted}"},
        ],
    )

    analysis = json.loads(
        response.choices[0].message.tool_calls[0].function.arguments
    )
""")

STEP3_CODE = textwrap.dedent("""\
    # Pattern 3: Role — Identity + Constraints + Context in the system prompt
    # ensures consistent tone, labels, and policy across every response.

    TRIAGE_AGENT_ROLE = \"\"\"
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
      critical  ->  data loss, security breach, or full outage
      high      ->  core feature broken for a segment of users
      medium    ->  degraded experience, workaround exists
      low       ->  cosmetic, edge case, or minor inconvenience
    \"\"\"

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=600,
        messages=[
            {"role": "system", "content": TRIAGE_AGENT_ROLE},
            {"role": "user",   "content": f"Write a Jira-style bug ticket ..."},
        ],
    )

    ticket = response.choices[0].message.content
""")


# ── UI ────────────────────────────────────────────────────────────────────────

EXAMPLE_REPORT = """hey team, so ive been trying to export my data for the past two days and it just doesnt work??? i click export, it spins for like 30 seconds then just says "export failed" with no error message. im on the enterprise plan and i NEED this data for a board presentation on friday. this is really urgent!!

i tried in chrome and safari, same thing. also tried with a smaller date range (last 30 days instead of last year) and THAT worked fine. so its definitely something with large exports. please fix asap"""

with gr.Blocks(title="Bug Triage System") as demo:
    gr.Markdown("# Bug Triage System")
    gr.Markdown("Paste a raw bug report. Watch the three-step pipeline turn it into a structured Jira ticket.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Raw Bug Report")
            report_input = gr.Textbox(
                label="",
                placeholder="Paste any bug report here — messy, emotional, unstructured...",
                lines=10,
                value=EXAMPLE_REPORT,
            )
            with gr.Row():
                run_btn = gr.Button("Run Triage", variant="primary")
                clear_btn = gr.Button("Clear Cache", variant="secondary")
            status = gr.Textbox(label="Status", interactive=False, lines=1)

        with gr.Column(scale=2):
            gr.Markdown("### Step 1 — Extract `(Schema)`")
            step1_out = gr.JSON(label="Output", show_label=False)
            with gr.Accordion("Show Code & Prompt", open=False):
                gr.Code(value=STEP1_CODE, language="python", lines=20, interactive=False)

            gr.Markdown("### Step 2 — Analyse `(Delegation)`")
            step2_out = gr.JSON(label="Output", show_label=False)
            with gr.Accordion("Show Code & Prompt", open=False):
                gr.Code(value=STEP2_CODE, language="python", lines=20, interactive=False)

            gr.Markdown("### Step 3 — Ticket `(Role)`")
            step3_out = gr.Textbox(label="", lines=10)
            with gr.Accordion("Show Code & Prompt", open=False):
                gr.Code(value=STEP3_CODE, language="python", lines=20, interactive=False)

    run_btn.click(
        fn=triage,
        inputs=report_input,
        outputs=[step1_out, step2_out, step3_out, status],
    )
    clear_btn.click(
        fn=clear_cache,
        inputs=None,
        outputs=status,
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
