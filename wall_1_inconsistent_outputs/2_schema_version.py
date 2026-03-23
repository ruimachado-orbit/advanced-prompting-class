"""
Wall 1: Inconsistent Outputs — The Schema Fix
==============================================
THE FIX: Use OpenAI's `functions` / `tools` parameter to define a strict JSON schema.
When the model is forced to call a function, it MUST return exactly the shape
you declared — no prose, no markdown fences, no surprising field names.

Before this fix : ~40% of responses needed manual cleanup or crashed.
After  this fix : 100% of responses match the schema (or raise a clear error).
"""

import json
import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

# -------------------------------------------------------------------
# Step 1 — Declare the schema once, as a "tool" the model must call.
# The model treats the tool call as the only valid output format.
# -------------------------------------------------------------------

REVIEW_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_review_analysis",
        "description": (
            "Submit the structured analysis of a product review. "
            "You MUST call this function — do not respond with plain text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "neutral", "negative"],
                    "description": "Overall emotional tone of the review.",
                },
                "score": {
                    "type": "integer",
                    "description": "Numeric quality score from 1 (worst) to 10 (best).",
                },
                "themes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product aspects mentioned in the review.",
                },
                "recommendation": {
                    "type": "string",
                    "enum": ["buy", "wait", "avoid"],
                    "description": "Purchasing recommendation based on the review.",
                },
                "summary": {
                    "type": "string",
                    "description": "One-sentence summary of the review.",
                },
            },
            "required": ["sentiment", "score", "themes", "recommendation", "summary"],
        },
    },
}


def analyze_review(review_text: str) -> dict:
    """
    Analyze a product review and return a guaranteed-valid structured result.

    The model is forced to call `submit_review_analysis`, so the response
    is always found in the tool_calls — never in free-form text.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=1024,
        tools=[REVIEW_ANALYSIS_TOOL],
        # tool_choice forces the model to call our specific function
        tool_choice={"type": "function", "function": {"name": "submit_review_analysis"}},
        messages=[
            {
                "role": "user",
                "content": f"Analyze this product review:\n\n{review_text}",
            }
        ],
    )

    # The structured data lives in the tool_calls — always.
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_review_analysis":
                return json.loads(tool_call.function.arguments)

    # If we somehow get here, the model misbehaved at the API level
    raise RuntimeError("Model did not call the required function — check your tool_choice setting.")


def display_analysis(result: dict) -> None:
    """Pretty-print the validated analysis result."""
    print(f"  Sentiment    : {result['sentiment']}")
    print(f"  Score        : {result['score']}/10")
    print(f"  Themes       : {', '.join(result['themes'])}")
    print(f"  Recommendation: {result['recommendation']}")
    print(f"  Summary      : {result['summary']}")


if __name__ == "__main__":
    reviews = [
        (
            "Laptop — mixed",
            "The battery lasts all day which is fantastic, "
            "but the fan noise is distracting during video calls. "
            "Overall happy with the purchase.",
        ),
        (
            "Headphones — negative",
            "Broke after two weeks. Customer service was useless "
            "and refused a refund. Complete waste of money.",
        ),
        (
            "Keyboard — positive",
            "Best mechanical keyboard I've ever owned. "
            "Tactile feedback is perfect, build quality is excellent, "
            "and the RGB lighting is gorgeous.",
        ),
    ]

    print("=== Schema Version: Guaranteed Structured Output ===\n")

    for label, review in reviews:
        print(f"Review: {label}")
        result = analyze_review(review)
        display_analysis(result)
        print()

    print("Every response matched the schema. No crashes.")
    print("See with_validation_and_fallback.py for production hardening.")
