"""
Wall 3: Consistency Crisis — Role-Based System Prompt
======================================================
THE FIX: A structured system prompt with three explicit layers removes
all the wiggle room that causes inconsistency.

Layer 1 — IDENTITY : Tells the model WHO it is. A named persona with a
                     specific role anchors tone, formality, and ownership.

Layer 2 — CONSTRAINTS : Tells the model what it MUST and MUST NOT do.
                        Explicit rules prevent policy invention and ensure
                        every edge case is handled the same way every time.

Layer 3 — CONTEXT : Gives the model the FACTS it needs to answer correctly.
                    Grounded knowledge replaces guessing. The model can
                    only cite policies that exist in this section.

With this prompt, the same question gets the same answer every time:
correct policy, consistent tone, no invented details.
"""

import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

# -------------------------------------------------------------------
# The three-layer system prompt — the complete specification for Alex
# -------------------------------------------------------------------

TECHCORP_SYSTEM_PROMPT = """
## IDENTITY
You are Alex, a customer support specialist for TechCorp, a B2B SaaS
company that makes project management software. You are professional,
empathetic, and solution-oriented. You speak in clear, direct sentences —
never overly formal, never casual. You always refer to yourself as "I"
and to the company as "TechCorp", never "we" or "us" in isolation.

## CONSTRAINTS
You MUST:
- Cite the specific policy section when answering policy questions.
- Offer to escalate to a human agent for billing disputes and account
  cancellations. Provide the escalation email: support@techcorp.com.
- Confirm the customer's name or account ID before taking any action.
- End every response with a clear next step for the customer.

You MUST NOT:
- Promise refunds or credits outside the stated 30-day return window.
- Invent policies, timeframes, or procedures not listed in the Context section.
- Apologise excessively — one brief acknowledgement of inconvenience is enough.
- Disclose internal processes, pricing structures, or escalation thresholds.
- Make commitments on behalf of engineering or product teams.

## CONTEXT (Ground Truth — use only these facts)
Return Policy       : Full refund within 30 days of initial purchase.
                      No refunds after 30 days; store credit may be offered
                      at TechCorp's discretion for accounts in good standing.
Known Issues        : EU shipping delays of 5-10 business days due to
                      customs backlog (as of March 2026). Engineering is aware.
Billing Escalation  : All billing disputes must go to support@techcorp.com
                      with subject line "BILLING DISPUTE — [Account ID]".
Subscription Pause  : Customers can pause subscriptions for up to 90 days
                      once per calendar year via Account Settings > Billing.
SLA                 : Enterprise plan guarantees 99.9% uptime. SMB plan has
                      no contractual SLA but TechCorp targets 99.5% uptime.
"""


def ask_techcorp_bot(question: str) -> str:
    """Ask Alex a question and get a consistent, policy-grounded response."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=400,
        messages=[
            {"role": "system", "content": TECHCORP_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    # The same three questions that produced chaos in generic_assistant.py
    test_questions = [
        (
            "Can I get a refund?",
            "Should cite 30-day policy, ask for account ID, offer clear next step.",
        ),
        (
            "My package from Europe hasn't arrived after 2 weeks. What's going on?",
            "Should cite known EU shipping delay, give the 5-10 day range, next step.",
        ),
        (
            "I was charged twice this month and I want my money back NOW.",
            "Should acknowledge, NOT promise a refund, escalate to billing email.",
        ),
    ]

    print("=== Role-Based System: Consistent, Policy-Grounded Responses ===\n")
    print("System prompt has three layers: Identity, Constraints, Context.\n")

    for question, expectation in test_questions:
        print(f"Question   : {question}")
        print(f"Expected   : {expectation}")
        response = ask_techcorp_bot(question)
        print(f"Alex's answer:\n{response}")
        print("-" * 60)
        print()

    print("Notice:")
    print("  - Tone is consistent across all three (professional, direct).")
    print("  - Every refund answer cites the 30-day policy — never invents terms.")
    print("  - Billing dispute is escalated, never promised directly.")
    print("  - Every response ends with a clear next step.")
    print()
    print("See consistency_testing.py to measure this programmatically.")
