"""
Wall 3: Consistency Crisis — Production Consistency Testing
============================================================
PRODUCTION PATTERN: You can't ship a support bot without verifying that
it behaves consistently across many runs. This file provides a framework
for measuring consistency programmatically.

`test_consistency()` sends the same message N times and checks whether
each response meets a set of defined assertions. A consistency score is
calculated as the percentage of assertions that pass across all runs.

A score of 100% means the bot behaves identically every time on that
assertion. Anything below ~90% signals a fragile behaviour that needs
a tighter system prompt before going to production.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Callable
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

# Reuse the robust system prompt from role_based_system.py
TECHCORP_SYSTEM_PROMPT = """
## IDENTITY
You are Alex, a customer support specialist for TechCorp, a B2B SaaS
company that makes project management software. You are professional,
empathetic, and solution-oriented. You speak in clear, direct sentences.

## CONSTRAINTS
You MUST:
- Cite the specific policy section when answering policy questions.
- Offer to escalate billing disputes to support@techcorp.com.
- End every response with a clear next step for the customer.

You MUST NOT:
- Promise refunds outside the 30-day return window.
- Invent policies, timeframes, or procedures not in the Context section.
- Disclose internal escalation thresholds.

## CONTEXT
Return Policy       : Full refund within 30 days of initial purchase.
                      No refunds after 30 days.
Billing Escalation  : All billing disputes to support@techcorp.com
                      with subject "BILLING DISPUTE — [Account ID]".
Subscription Pause  : Customers can pause for up to 90 days once per year
                      via Account Settings > Billing.
SLA                 : Enterprise plan guarantees 99.9% uptime.
"""


# -------------------------------------------------------------------
# Assertion helpers — each returns (passed: bool, detail: str)
# -------------------------------------------------------------------

def mentions_30_day_policy(response: str) -> tuple[bool, str]:
    """The response must reference the 30-day refund window."""
    found = "30" in response and ("day" in response.lower() or "days" in response.lower())
    return found, "mentions 30-day policy" if found else "did NOT mention 30-day policy"


def mentions_escalation_email(response: str) -> tuple[bool, str]:
    """For billing disputes, the response must give the escalation email."""
    found = "support@techcorp.com" in response
    return found, "includes escalation email" if found else "missing escalation email"


def does_not_invent_numbers(response: str) -> tuple[bool, str]:
    """
    Check that the model isn't inventing refund percentages or day counts
    other than the ones explicitly in the system prompt (30, 90, 99.9, 99.5).
    """
    allowed_numbers = {"30", "90", "99.9", "99.5"}
    # Find all standalone numbers in the response
    found_numbers = set(re.findall(r'\b\d+\.?\d*\b', response))
    suspicious = found_numbers - allowed_numbers - {"1", "2", "3", "4", "5"}  # small ordinals OK
    # Filter out years and innocuous counts
    suspicious = {n for n in suspicious if float(n) > 5 and float(n) != 2026}
    passed = len(suspicious) == 0
    detail = (
        "no invented numbers" if passed
        else f"suspicious numbers found: {suspicious}"
    )
    return passed, detail


def ends_with_next_step(response: str) -> tuple[bool, str]:
    """The response should end with an actionable next step."""
    action_words = [
        "please", "contact", "visit", "go to", "reach out", "send",
        "let me know", "feel free", "reply", "you can", "would you"
    ]
    last_200 = response[-200:].lower()
    found = any(word in last_200 for word in action_words)
    return found, "ends with next step" if found else "no clear next step at end"


def no_excessive_apology(response: str) -> tuple[bool, str]:
    """Detect over-apologetic language — a sign of an untethered persona."""
    apology_pattern = re.compile(
        r"(i('m| am) so sorry|i sincerely apologize|deeply sorry|i apologize profusely)",
        re.IGNORECASE,
    )
    found = bool(apology_pattern.search(response))
    return not found, "no excessive apology" if not found else "contains excessive apology"


# -------------------------------------------------------------------
# Test runner
# -------------------------------------------------------------------

@dataclass
class AssertionResult:
    name: str
    passed: bool
    detail: str


@dataclass
class RunResult:
    run_number: int
    response: str
    assertions: list[AssertionResult] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for a in self.assertions if a.passed)

    @property
    def total_count(self) -> int:
        return len(self.assertions)


def ask_bot(question: str) -> str:
    """Single call to the TechCorp bot."""
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=400,
        messages=[
            {"role": "system", "content": TECHCORP_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def test_consistency(
    question: str,
    assertions: list[tuple[str, Callable[[str], tuple[bool, str]]]],
    n_runs: int = 5,
) -> dict:
    """
    Send `question` to the bot `n_runs` times and evaluate each response
    against every assertion. Returns a full report including a consistency
    score per assertion and an overall score.

    Args:
        question   : The message to send each time.
        assertions : List of (name, checker_fn) tuples.
        n_runs     : How many times to send the same question.
    """
    print(f'Testing: "{question}"')
    print(f"Running {n_runs} calls …\n")

    all_runs: list[RunResult] = []

    for i in range(1, n_runs + 1):
        response = ask_bot(question)
        run = RunResult(run_number=i, response=response)

        for assertion_name, checker in assertions:
            passed, detail = checker(response)
            run.assertions.append(AssertionResult(assertion_name, passed, detail))

        pass_rate = run.pass_count / run.total_count * 100
        print(f"  Run {i}: {run.pass_count}/{run.total_count} assertions passed ({pass_rate:.0f}%)")
        all_runs.append(run)

    # Per-assertion consistency scores
    assertion_scores = {}
    for assertion_name, _ in assertions:
        passed_runs = sum(
            1 for run in all_runs
            if any(a.name == assertion_name and a.passed for a in run.assertions)
        )
        assertion_scores[assertion_name] = passed_runs / n_runs * 100

    overall_score = sum(assertion_scores.values()) / len(assertion_scores)

    return {
        "question":         question,
        "n_runs":           n_runs,
        "assertion_scores": assertion_scores,
        "overall_score":    round(overall_score, 1),
        "runs":             all_runs,
    }


def print_report(report: dict) -> None:
    print(f"\n{'=' * 60}")
    print(f"CONSISTENCY REPORT")
    print(f"Question : {report['question']}")
    print(f"Runs     : {report['n_runs']}")
    print(f"{'=' * 60}")
    print("\nPer-assertion consistency scores:")
    for name, score in report["assertion_scores"].items():
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        status = "PASS" if score >= 90 else "REVIEW" if score >= 70 else "FAIL"
        print(f"  [{status}] {bar} {score:5.1f}%  {name}")
    print(f"\nOverall consistency score: {report['overall_score']}%")
    threshold = 90
    verdict = "SHIP-READY" if report["overall_score"] >= threshold else "NEEDS WORK"
    print(f"Verdict: {verdict} (threshold: {threshold}%)")


if __name__ == "__main__":
    print("=== Consistency Testing: Measuring Bot Reliability ===\n")

    # Test 1: Refund question — must always cite 30-day policy
    refund_report = test_consistency(
        question="Can I get a refund for my subscription?",
        assertions=[
            ("mentions 30-day policy",    mentions_30_day_policy),
            ("no invented numbers",       does_not_invent_numbers),
            ("ends with next step",       ends_with_next_step),
            ("no excessive apology",      no_excessive_apology),
        ],
        n_runs=5,
    )
    print_report(refund_report)

    print("\n" + "=" * 60 + "\n")

    # Test 2: Billing dispute — must always give escalation path
    billing_report = test_consistency(
        question="I was charged twice and I want a refund immediately.",
        assertions=[
            ("mentions escalation email", mentions_escalation_email),
            ("mentions 30-day policy",    mentions_30_day_policy),
            ("no invented numbers",       does_not_invent_numbers),
            ("ends with next step",       ends_with_next_step),
        ],
        n_runs=5,
    )
    print_report(billing_report)

    print("\nLow scores (<90%) indicate the system prompt needs tightening.")
    print("Run this suite after every system prompt change to catch regressions.")
