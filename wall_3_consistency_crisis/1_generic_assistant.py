"""
Wall 3: Consistency Crisis — The Generic Assistant Problem
==========================================================
THE PROBLEM: A vague or missing system prompt lets the model improvise.
Each request gets whatever personality, policy stance, and communication
style felt appropriate at inference time. For a customer support bot,
this is dangerous: users get contradictory information, invented policies,
and wildly different tones — sometimes in the same day.

The three simulated responses below show what a "Be helpful" system
prompt produces for the same question asked three different times.
"""

import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

# The vague system prompt that causes all the problems.
# "Be helpful" gives the model zero constraints — so it invents them.
VAGUE_SYSTEM_PROMPT = "Be helpful."

CUSTOMER_QUESTION = "Can I get a refund?"


def ask_generic_bot(question: str, run_label: str) -> str:
    """Send a question with no real system prompt. Watch the chaos."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=300,
        messages=[
            {"role": "system", "content": VAGUE_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


# -------------------------------------------------------------------
# Three real-world response patterns you get with a vague system prompt.
# Same question. Same model. Three completely different experiences.
# -------------------------------------------------------------------

SIMULATED_RESPONSE_A = """
I'm so sorry to hear you're having trouble! Of course, I completely
understand your frustration. Refunds are absolutely available and
I want to make sure you're 100% satisfied. Just let me know your
order number and I'll process that right away for you.
"""
# Problem: Over-apologetic, promises unlimited refunds with no policy check,
# creates false expectations that will make the next agent's job harder.

SIMULATED_RESPONSE_B = """
Refund eligibility depends on various factors. You would need to check
the terms and conditions that you agreed to at the time of purchase.
Generally speaking, refunds may or may not be available depending on
the situation. Please review your purchase agreement for details.
"""
# Problem: Useless. Doesn't tell the customer anything actionable.
# "Check your terms" is a brush-off, not support.

SIMULATED_RESPONSE_C = """
Yes, we offer refunds within 30 days of purchase for most items.
However, digital downloads, subscription fees after the first month,
and items marked as final sale are non-refundable. You'll also need
the original receipt and the product must be in unused condition.
"""
# Problem: This looks reasonable — but TechCorp's ACTUAL policy is different.
# The model invented specific details (digital downloads, original receipt)
# that aren't in any real policy document. This is policy hallucination.


if __name__ == "__main__":
    print("=== Generic Assistant: Consistency Crisis Demo ===\n")
    print(f'System prompt: "{VAGUE_SYSTEM_PROMPT}"')
    print(f'Customer question: "{CUSTOMER_QUESTION}"\n')

    print("--- Simulated Response A (Over-apologetic, promises everything) ---")
    print(SIMULATED_RESPONSE_A)

    print("--- Simulated Response B (Dismissive, unhelpful) ---")
    print(SIMULATED_RESPONSE_B)

    print("--- Simulated Response C (Confident but INVENTED policy details) ---")
    print(SIMULATED_RESPONSE_C)

    print("=" * 60)
    print("All three responses are to the EXACT same question.")
    print("Three different tones. Three different policy stances.")
    print("One of them invents facts. None of them are safe to ship.")
    print()

    print("Running live call with vague system prompt (result will vary):")
    print("-" * 60)
    live_response = ask_generic_bot(CUSTOMER_QUESTION, "live")
    print(live_response)
    print()
    print("See role_based_system.py for the fix.")
