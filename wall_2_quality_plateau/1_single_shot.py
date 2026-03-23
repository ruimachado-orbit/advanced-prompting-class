"""
Wall 2: Quality Plateau — The Single-Shot Problem
==================================================
THE PROBLEM: One mega-prompt trying to do everything at once produces
shallow, generic output. The model has to simultaneously understand
the data, analyse it, prioritise findings, AND write polished prose —
with a single context window and no room to specialise.

The output below is "technically correct" but would embarrass you in
front of a VP. It lacks depth, specificity, and actionable insight.
"""

import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

# -------------------------------------------------------------------
# Sample customer feedback (realistic SaaS product scenario)
# -------------------------------------------------------------------
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


def analyze_feedback_single_shot(feedback: str) -> str:
    """
    Ask the model to do everything in one prompt.
    The result will be generic because the model is context-switching
    between four cognitive tasks simultaneously.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Analyze this customer feedback, identify themes, "
                    "suggest product improvements, and write an executive summary:\n\n"
                    + feedback
                ),
            }
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Typical single-shot output (what you actually get):
# -------------------------------------------------------------------
SAMPLE_BAD_OUTPUT = """
The customer feedback reveals several themes including performance,
documentation, support, and feature requests. Enterprise customers
seem to have different needs than SMB customers.

Suggested improvements:
- Improve performance
- Update documentation
- Improve support response times
- Add more integrations
- Fix bugs

Executive Summary:
Customer feedback is mixed. Some customers are happy while others
are frustrated. The team should focus on addressing the most common
complaints to improve overall satisfaction and reduce churn risk.
"""
# Notice what's missing:
# - No frequency analysis (how many customers hit each issue?)
# - No severity ranking (which issues cause churn vs. minor friction?)
# - No business impact estimate (enterprise customers = higher ACV)
# - No specific, actionable recommendations with owners
# - The "executive summary" could describe any SaaS product ever made


if __name__ == "__main__":
    print("=== Single-Shot Version: One Prompt Does Everything ===\n")
    print("Sending one mega-prompt to LLM...\n")

    result = analyze_feedback_single_shot(CUSTOMER_FEEDBACK)

    print("Model output:")
    print("-" * 60)
    print(result)
    print("-" * 60)
    print("\nNotice: output is shallow and generic.")
    print("It names themes but doesn't quantify them.")
    print("It suggests 'fix bugs' without saying which bug, for whom, or why now.")
    print("\nSee multi_step_delegation.py for the fix.")
