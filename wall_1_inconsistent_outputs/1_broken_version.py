"""
Wall 1: Inconsistent Outputs — The Broken Version
==================================================
THE PROBLEM: Asking the model for structured data with a plain text prompt
gives you different formats every time. Your parser assumes one shape,
the model returns another, and your app crashes in production.

Run this file to see the inconsistency problem in action.
"""

from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI()

# -------------------------------------------------------------------
# Three real outputs the model might return for the SAME prompt.
# All are "correct" English, but they'll break any downstream parser.
# -------------------------------------------------------------------

RAW_OUTPUT_1 = """
{
  "sentiment": "positive",
  "score": 8,
  "themes": ["battery life", "screen quality"],
  "recommendation": "Buy it"
}
"""

RAW_OUTPUT_2 = """
The review has an overall **positive tone** (roughly 7/10).
Key themes: great camera, minor heating issue.
I would recommend this product for most users.
"""

RAW_OUTPUT_3 = """
```json
{
  "tone": "mixed",
  "rating": 6,
  "topics": ["performance", "price"],
  "verdict": "Decent value for money"
}
```
"""

# Notice: output 1 uses "sentiment", output 3 uses "tone".
# Output 1 uses "score", output 3 uses "rating".
# Output 1 uses "themes", output 3 uses "topics".
# Output 2 is pure prose — no JSON at all.


def parse_review(raw_text: str) -> dict:
    """
    Naive parser that assumes the model always returns clean JSON
    with a predictable schema. This WILL crash on outputs 2 and 3.
    """
    import json

    # Strip markdown fences — but only if we remember to do it...
    cleaned = raw_text.strip()
    data = json.loads(cleaned)          # Crashes on prose (output 2)

    # Hard-coded field names from the first response we ever tested
    return {
        "sentiment": data["sentiment"],  # Crashes on output 3 ("tone")
        "score": data["score"],          # Crashes on output 3 ("rating")
        "themes": data["themes"],        # Crashes on output 3 ("topics")
    }


def analyze_review_broken(review_text: str) -> dict:
    """
    Sends a plain-language prompt and hopes the model returns
    the exact JSON shape we need. It won't — not reliably.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyze this product review and return JSON with sentiment, "
                    f"score (1-10), themes, and recommendation:\n\n{review_text}"
                ),
            }
        ],
    )

    raw = response.choices[0].message.content
    print("Raw model output:\n", raw)
    print("-" * 60)

    # This will crash unpredictably depending on what the model returned
    return parse_review(raw)


if __name__ == "__main__":
    sample_review = (
        "I've been using this laptop for three months. "
        "The battery lasts all day which is fantastic, "
        "but the fan noise is distracting during video calls. "
        "Overall I'm happy with the purchase."
    )

    print("=== Broken Version: Inconsistent Output Demo ===\n")
    print("Simulating what different runs return (see RAW_OUTPUT_* constants above).")
    print("Attempting to parse each one with the naive parser...\n")

    for label, raw in [("Output 1 (clean JSON)", RAW_OUTPUT_1),
                       ("Output 2 (prose)",      RAW_OUTPUT_2),
                       ("Output 3 (fenced JSON, different keys)", RAW_OUTPUT_3)]:
        print(f"--- {label} ---")
        try:
            result = parse_review(raw)
            print("Parsed OK:", result)
        except Exception as e:
            print(f"CRASH: {type(e).__name__}: {e}")
        print()

    print("Lesson: plain-text prompts give you inconsistent formats.")
    print("See schema_version.py for the fix.")
