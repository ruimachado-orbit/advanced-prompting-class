"""
Wall 2: Quality Plateau — Multi-Step Delegation (Sequential)
=============================================================
THE FIX: Break the task into three specialised steps where each model
call has one job and one job only. The output of each step becomes
the grounded input of the next — so later steps never have to hallucinate
context they should have derived from the data.

Step 1 (Extract)   : Read raw feedback → produce a structured list of
                     themes and pain points. Pure extraction, no opinions.
Step 2 (Analyse)   : Take the extracted themes → assess frequency,
                     severity, and business impact. No writing yet.
Step 3 (Synthesise): Take the analysis → write a compelling exec summary
                     with specific, prioritised recommendations.

Quality comparison:
  Single-shot  : Generic bullet points. Could describe any SaaS company.
  Multi-step   : Specific insights tied to actual quotes, frequency counts,
                 revenue impact estimates, and named next actions.
"""

import json
import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

CUSTOMER_FEEDBACK = """
Feedback #1 (Enterprise, 4/5): The dashboard loads slowly when we have
more than 500 projects. Our team loves the reporting features though.

Feedback #2 (SMB, 2/5): Spent 3 hours trying to set up SSO. The docs
are outdated and support took 2 days to respond. Almost churned.

Feedback #3 (Enterprise, 3/5): Data export is broken for date ranges
over 90 days. We've raised this ticket twice. Still not fixed.

Feedback #4 (SMB, 5/5): Best onboarding experience I've had with any
B2B tool. The setup wizard is intuitive and the video tutorials helped.

Feedback #5 (Enterprise, 2/5): We need better role-based permissions.
Right now it's all-or-nothing admin access which is a security risk.

Feedback #6 (SMB, 4/5): Integrations with Slack and Jira work great.
Would love a Salesforce connector though.

Feedback #7 (Enterprise, 1/5): Experienced three outages in one month.
Each lasted 2-4 hours. This is completely unacceptable for our SLAs.
"""


# -------------------------------------------------------------------
# Step 1: Extract — raw themes and pain points, no interpretation
# -------------------------------------------------------------------

def step1_extract_themes(feedback: str) -> str:
    """
    Focused extraction only. The system prompt forbids the model from
    doing analysis or writing recommendations — it just reads and lists.
    This produces a clean, structured intermediate artefact.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data extraction specialist. Your only job is to read "
                    "customer feedback verbatim and extract themes and pain points. "
                    "Do NOT analyse, evaluate, or recommend anything yet. "
                    "Output a JSON object with a 'themes' array. Each theme has: "
                    "name, affected_segments (list of 'Enterprise'/'SMB'), "
                    "verbatim_quotes (list of direct quotes), and mention_count (integer)."
                ),
            },
            {
                "role": "user",
                "content": f"Extract all themes from this feedback:\n\n{feedback}",
            },
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Step 2: Analyse — depth analysis on the structured extraction
# -------------------------------------------------------------------

def step2_analyse_themes(extracted_themes: str) -> str:
    """
    The model receives clean structured data (from step 1) and can now
    focus entirely on analysis: severity, business impact, churn risk.
    It never has to re-read raw feedback — the extraction already did that.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior product analyst. You receive pre-extracted theme data "
                    "and your job is to produce a deep business analysis. "
                    "For each theme, assess: severity (critical/high/medium/low), "
                    "churn_risk (high/medium/low), estimated_revenue_impact "
                    "(assume Enterprise = $50k ACV, SMB = $8k ACV), and "
                    "effort_to_fix (high/medium/low). "
                    "Rank themes by priority (revenue_at_risk × churn_risk). "
                    "Output structured JSON."
                ),
            },
            {
                "role": "user",
                "content": f"Analyse these extracted themes:\n\n{extracted_themes}",
            },
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Step 3: Synthesise — executive summary from the analysis
# -------------------------------------------------------------------

def step3_synthesise_summary(analysis: str) -> str:
    """
    The model now has a rich, quantified analysis as its input.
    It can write a genuinely specific, data-backed executive summary
    instead of generic platitudes — because all the hard thinking
    was done in the previous steps.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an executive communication specialist who writes for VP-level "
                    "audiences. Transform product analysis data into a crisp, compelling "
                    "executive summary. Rules: lead with business impact in dollars, "
                    "name the top 3 priorities with specific actions and owners, "
                    "include one 'bright spot' to balance the narrative, "
                    "end with a 30-day action plan. Be specific — no generic advice."
                ),
            },
            {
                "role": "user",
                "content": f"Write an executive summary from this analysis:\n\n{analysis}",
            },
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Orchestrator — chains the three steps together
# -------------------------------------------------------------------

def analyze_feedback_multi_step(feedback: str) -> dict:
    """
    Runs all three steps in sequence, passing each output as input
    to the next step. Returns all intermediate outputs for visibility.
    """
    print("  Step 1: Extracting themes …")
    themes = step1_extract_themes(feedback)

    print("  Step 2: Analysing themes …")
    analysis = step2_analyse_themes(themes)

    print("  Step 3: Synthesising executive summary …")
    summary = step3_synthesise_summary(analysis)

    return {
        "step1_extraction": themes,
        "step2_analysis":   analysis,
        "step3_summary":    summary,
    }


if __name__ == "__main__":
    print("=== Multi-Step Delegation: Sequential Pipeline ===\n")
    results = analyze_feedback_multi_step(CUSTOMER_FEEDBACK)

    print("\n--- Step 1: Extracted Themes ---")
    print(results["step1_extraction"])

    print("\n--- Step 2: Business Analysis ---")
    print(results["step2_analysis"])

    print("\n--- Step 3: Executive Summary ---")
    print(results["step3_summary"])

    print("\n" + "=" * 60)
    print("Notice: the summary cites actual numbers, segments, and")
    print("priorities — because each step built on real extracted data.")
    print("See parallel_delegation.py for running steps concurrently.")
