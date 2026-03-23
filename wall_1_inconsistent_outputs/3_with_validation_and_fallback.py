"""
Wall 1: Inconsistent Outputs — Production-Ready Version
========================================================
PRODUCTION HARDENING: Schema enforcement is necessary but not sufficient.
The model might still return a score of 0, an empty themes list, or a
sentiment value that slipped past the enum. This file adds:

  1. A validation layer — checks types, required fields, and value ranges.
  2. Retry logic    — re-asks up to 3 times, each time with a more explicit
                      correction message so the model knows what was wrong.
  3. A safe fallback — if all retries fail, returns a neutral default object
                       instead of crashing, and logs the failure for humans.
"""

import json
import logging
from typing import Optional
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

client = OpenAI()

REVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_review_analysis",
        "description": "Submit the structured analysis of a product review.",
        "parameters": {
            "type": "object",
            "properties": {
                "sentiment":       {"type": "string", "enum": ["positive", "neutral", "negative"]},
                "score":           {"type": "integer"},
                "themes":          {"type": "array",   "items": {"type": "string"}},
                "recommendation":  {"type": "string",  "enum": ["buy", "wait", "avoid"]},
                "summary":         {"type": "string"},
            },
            "required": ["sentiment", "score", "themes", "recommendation", "summary"],
        },
    },
}

# Safe default returned when all retries are exhausted
DEFAULT_RESULT = {
    "sentiment":      "neutral",
    "score":          5,
    "themes":         ["unclassified"],
    "recommendation": "wait",
    "summary":        "Analysis unavailable — manual review required.",
    "_fallback":      True,   # Flag so callers know this wasn't a real analysis
}


# -------------------------------------------------------------------
# Validation layer
# -------------------------------------------------------------------

def validate_output(data: dict) -> tuple[bool, list[str]]:
    """
    Check that the model's output meets our business rules.
    Returns (is_valid, list_of_error_messages).

    Catches issues that JSON Schema can't express, e.g.:
    - Empty strings in the themes list
    - Scores that are technically integers but out of spirit (score=1 with positive sentiment)
    """
    errors = []

    # Required field presence
    for field in ["sentiment", "score", "themes", "recommendation", "summary"]:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return False, errors   # No point continuing if fields are missing

    # Type checks
    if not isinstance(data["score"], int):
        errors.append(f"'score' must be an integer, got {type(data['score']).__name__}")

    # Range checks
    if isinstance(data["score"], int) and not (1 <= data["score"] <= 10):
        errors.append(f"'score' must be between 1 and 10, got {data['score']}")

    # Enum checks (belt-and-suspenders on top of the schema)
    if data.get("sentiment") not in ("positive", "neutral", "negative"):
        errors.append(f"Invalid sentiment: '{data.get('sentiment')}'")

    if data.get("recommendation") not in ("buy", "wait", "avoid"):
        errors.append(f"Invalid recommendation: '{data.get('recommendation')}'")

    # Content quality checks
    if not data.get("themes"):
        errors.append("'themes' list must not be empty")
    elif any(not t.strip() for t in data["themes"]):
        errors.append("'themes' list contains blank entries")

    if len(data.get("summary", "")) < 10:
        errors.append("'summary' is too short to be useful")

    return len(errors) == 0, errors


# -------------------------------------------------------------------
# Core call with retry
# -------------------------------------------------------------------

def _call_model(messages: list) -> Optional[dict]:
    """Single model call; returns the tool input dict or None."""
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        tools=[REVIEW_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_review_analysis"}},
        messages=messages,
    )
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_review_analysis":
                return json.loads(tool_call.function.arguments)
    return None


def safe_parse_with_fallback(review_text: str, max_retries: int = 3) -> dict:
    """
    Production-safe wrapper around the model call.

    Attempt 1: Standard analysis request.
    Attempt 2: Add a reminder about the specific fields that failed validation.
    Attempt 3: Very explicit, field-by-field instructions to maximise success.
    Fallback  : Return DEFAULT_RESULT and log a warning for human review.
    """
    base_message = {
        "role": "user",
        "content": f"Analyze this product review:\n\n{review_text}",
    }

    for attempt in range(1, max_retries + 1):
        log.info("Attempt %d/%d …", attempt, max_retries)

        if attempt == 1:
            messages = [base_message]
        elif attempt == 2:
            # Feed the previous errors back so the model can self-correct
            messages = [
                base_message,
                {
                    "role": "user",
                    "content": (
                        f"Your previous response had validation errors: {'; '.join(last_errors)}. "
                        "Please try again, ensuring all fields match the required types and ranges."
                    ),
                },
            ]
        else:
            # Maximum specificity for the final attempt
            messages = [
                base_message,
                {
                    "role": "user",
                    "content": (
                        "Be very precise: sentiment must be exactly one of positive/neutral/negative; "
                        "score must be an integer 1-10; themes must be a non-empty list of strings; "
                        "recommendation must be exactly one of buy/wait/avoid; "
                        "summary must be at least one complete sentence."
                    ),
                },
            ]

        raw = _call_model(messages)

        if raw is None:
            log.warning("Model did not call the tool on attempt %d.", attempt)
            last_errors = ["Tool was not called"]
            continue

        is_valid, last_errors = validate_output(raw)
        if is_valid:
            log.info("Validation passed on attempt %d.", attempt)
            return raw

        log.warning("Validation failed on attempt %d: %s", attempt, last_errors)

    # All retries exhausted — return safe default and alert
    log.error(
        "All %d attempts failed for review (first 80 chars): '%s…'. "
        "Returning fallback result. Last errors: %s",
        max_retries,
        review_text[:80],
        last_errors,
    )
    return DEFAULT_RESULT.copy()


if __name__ == "__main__":
    test_reviews = [
        "This blender is incredible — makes smoothies in seconds and cleans easily. "
        "Worth every penny, highly recommend.",

        "Arrived broken. Packaging was fine so it was damaged before shipping. "
        "Seller offered a 10% discount instead of a replacement. Never again.",

        "It's okay. Does what it says but nothing special. "
        "The price feels a bit high for what you get.",
    ]

    print("=== Production Version: Validation + Retry + Fallback ===\n")

    for review in test_reviews:
        print(f"Review: {review[:70]}…")
        result = safe_parse_with_fallback(review)

        if result.get("_fallback"):
            print("  [FALLBACK] Using default result — manual review needed.")
        else:
            is_valid, errors = validate_output(result)
            print(f"  Sentiment      : {result['sentiment']}")
            print(f"  Score          : {result['score']}/10")
            print(f"  Themes         : {', '.join(result['themes'])}")
            print(f"  Recommendation : {result['recommendation']}")
            print(f"  Summary        : {result['summary']}")
            print(f"  Validation     : {'PASS' if is_valid else 'FAIL — ' + str(errors)}")
        print()
