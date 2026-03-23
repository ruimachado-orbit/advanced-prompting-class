"""
Wall 2: Quality Plateau — Parallel Delegation
==============================================
ADVANCED PATTERN: Some analysis steps are fully independent of each other.
Running them sequentially is wasteful — you wait for UX analysis before
starting performance analysis, even though neither depends on the other.

This file uses Python's `concurrent.futures.ThreadPoolExecutor` to fire
three specialised analysis calls simultaneously, then merges the results.

Speedup:
  Sequential 3 calls × ~4s each = ~12s total
  Parallel   3 calls in parallel = ~4-5s total  (3x faster)

The merge step is a fourth, sequential call that takes all three parallel
outputs and synthesises a unified report. Only the merge needs to wait.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
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
# Three independent specialist analysers — safe to run in parallel
# -------------------------------------------------------------------

def analyse_ux_issues(feedback: str) -> str:
    """Specialist: UX and usability pain points only."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=800,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a UX research specialist. Extract only UX and usability "
                    "issues from customer feedback. Focus on: navigation confusion, "
                    "setup friction, documentation gaps, onboarding problems, and "
                    "workflow inefficiencies. Ignore performance and feature requests. "
                    "Return a JSON object with 'ux_issues' array, each with 'issue', "
                    "'affected_segment', 'severity' (high/medium/low), and 'quote'."
                ),
            },
            {"role": "user", "content": feedback},
        ],
    )
    return response.choices[0].message.content


def analyse_performance_issues(feedback: str) -> str:
    """Specialist: Performance, reliability, and stability issues only."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=800,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a site reliability engineer reviewing customer feedback. "
                    "Extract only performance, reliability, and stability issues. "
                    "Focus on: load times, outages, broken features, data errors, "
                    "and SLA violations. Ignore UX and feature requests. "
                    "Return a JSON object with 'performance_issues' array, each with "
                    "'issue', 'affected_segment', 'severity' (critical/high/medium/low), "
                    "'frequency', and 'quote'."
                ),
            },
            {"role": "user", "content": feedback},
        ],
    )
    return response.choices[0].message.content


def analyse_feature_requests(feedback: str) -> str:
    """Specialist: Feature gaps and product requests only."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=800,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a product manager reviewing customer feedback. "
                    "Extract only feature requests, missing capabilities, and integration "
                    "gaps. Ignore bugs and UX issues. "
                    "Return a JSON object with 'feature_requests' array, each with "
                    "'feature', 'affected_segment', 'business_value' (high/medium/low), "
                    "and 'quote'."
                ),
            },
            {"role": "user", "content": feedback},
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Merge step — sequential, runs after all parallel calls complete
# -------------------------------------------------------------------

def merge_analyses(ux: str, performance: str, features: str) -> str:
    """
    Takes the three specialist reports and produces a unified product brief.
    This step MUST be sequential — it needs all three inputs to be ready.
    """
    combined = f"""
UX ANALYSIS:
{ux}

PERFORMANCE ANALYSIS:
{performance}

FEATURE REQUEST ANALYSIS:
{features}
"""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Head of Product synthesising specialist reports. "
                    "Merge three parallel analyses into one unified product brief. "
                    "Deduplicate overlapping findings, rank all items by combined "
                    "business impact, and produce: (1) a priority matrix, "
                    "(2) the top 5 actions for the next sprint, "
                    "(3) a one-paragraph stakeholder summary."
                ),
            },
            {"role": "user", "content": combined},
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Parallel orchestrator
# -------------------------------------------------------------------

def analyze_feedback_parallel(feedback: str) -> dict:
    """
    Runs the three specialist analysers in parallel using a thread pool,
    waits for all to complete, then merges the results.
    """
    import time

    analysts: dict[str, Callable] = {
        "ux":          analyse_ux_issues,
        "performance": analyse_performance_issues,
        "features":    analyse_feature_requests,
    }

    results = {}
    start = time.time()

    # Fire all three calls simultaneously
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_label = {
            executor.submit(fn, feedback): label
            for label, fn in analysts.items()
        }

        for future in as_completed(future_to_label):
            label = future_to_label[future]
            try:
                results[label] = future.result()
                print(f"  [{label}] analysis complete ({time.time() - start:.1f}s)")
            except Exception as exc:
                print(f"  [{label}] FAILED: {exc}")
                results[label] = f'{{"error": "{exc}"}}'

    parallel_duration = time.time() - start
    print(f"\n  All parallel calls finished in {parallel_duration:.1f}s")
    print("  Merging results …")

    merge_start = time.time()
    merged = merge_analyses(
        results.get("ux", "{}"),
        results.get("performance", "{}"),
        results.get("features", "{}"),
    )
    total_duration = time.time() - start
    print(f"  Merge complete. Total wall-clock time: {total_duration:.1f}s")
    print(f"  (Sequential equivalent would be ~{parallel_duration * 3:.0f}s)")

    return {
        "ux_analysis":          results.get("ux"),
        "performance_analysis": results.get("performance"),
        "feature_analysis":     results.get("features"),
        "merged_report":        merged,
        "wall_clock_seconds":   round(total_duration, 1),
    }


if __name__ == "__main__":
    print("=== Parallel Delegation: Three Specialists Running Simultaneously ===\n")
    output = analyze_feedback_parallel(CUSTOMER_FEEDBACK)

    print("\n--- UX Issues ---")
    print(output["ux_analysis"])

    print("\n--- Performance Issues ---")
    print(output["performance_analysis"])

    print("\n--- Feature Requests ---")
    print(output["feature_analysis"])

    print("\n--- Merged Product Brief ---")
    print(output["merged_report"])

    print(f"\nTotal time: {output['wall_clock_seconds']}s")
