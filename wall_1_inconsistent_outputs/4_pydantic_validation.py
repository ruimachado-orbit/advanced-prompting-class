"""
Wall 1: Inconsistent Outputs — Pydantic Validation Layer
=========================================================
THE PATTERN: Use Pydantic models as a validation contract between
your AI and your application code.

Instead of writing manual type checks and range validators, you define
a Pydantic model that describes exactly what a valid response looks like.
Passing the AI output through the model does two things at once:
  1. Validates structure and types (raises ValidationError if wrong)
  2. Returns a typed Python object your IDE can autocomplete

This pairs naturally with the tool_use schema from 2_schema_version.py:
  - The tool schema tells Claude what shape to produce
  - The Pydantic model catches anything that still slips through

Run:
    pip install openai pydantic
    python 4_pydantic_validation.py
"""

import json
import os
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from pydantic import BaseModel, Field, field_validator


client = OpenAI()


# ============================================================
# Step 1 — Define your contract as a Pydantic model
#
# This is the single source of truth for what a valid
# AI response looks like. Your IDE knows the field names.
# Your tests can import this class. Your team can read it.
# ============================================================

class EventBookingOutput(BaseModel):
    event_id:    str = Field(..., description="Unique event identifier")
    title:       str = Field(..., min_length=3, description="Event title")
    location:    str = Field(..., description="Where the event takes place")
    attendees:   int = Field(..., ge=1, le=500, description="Number of attendees")
    confirmed:   bool = Field(..., description="Whether booking is confirmed")

    @field_validator("event_id")
    @classmethod
    def event_id_must_be_uppercase(cls, v: str) -> str:
        """Business rule: all event IDs are uppercase in our system."""
        if not v.isupper():
            raise ValueError(f"event_id must be uppercase, got '{v}'")
        return v


# ============================================================
# Step 2 — Define the tool schema Claude must fill
# (mirrors the Pydantic model — one defines AI output,
#  the other validates it on arrival)
# ============================================================

EVENT_BOOKING_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_event_booking",
        "description": "Submit the structured event booking details. You MUST call this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id":  {"type": "string",  "description": "Unique event identifier, uppercase"},
                "title":     {"type": "string",  "description": "Event title"},
                "location":  {"type": "string",  "description": "Where the event takes place"},
                "attendees": {"type": "integer", "description": "Number of attendees (1-500)"},
                "confirmed": {"type": "boolean", "description": "Whether booking is confirmed"},
            },
            "required": ["event_id", "title", "location", "attendees", "confirmed"],
        },
    },
}


# ============================================================
# Step 3 — Extract from AI, validate with Pydantic
# ============================================================

def extract_event_details(raw_request: str) -> EventBookingOutput:
    """
    Send raw booking request to the model, get structured output back,
    validate it with Pydantic.

    If the AI output doesn't match EventBookingOutput's rules,
    Pydantic raises a ValidationError immediately — before the
    bad data reaches your database.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=512,
        tools=[EVENT_BOOKING_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_event_booking"}},
        messages=[{"role": "user", "content": f"Extract booking details:\n\n{raw_request}"}],
    )

    # Get raw dict from the tool call
    raw_dict = None
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_event_booking":
                raw_dict = json.loads(tool_call.function.arguments)
                break

    if raw_dict is None:
        raise RuntimeError("Model did not call the required tool")

    # Pydantic validates and returns a typed object
    # Raises pydantic.ValidationError if anything is wrong
    return EventBookingOutput(**raw_dict)


# ============================================================
# Demo — valid and invalid cases
# ============================================================

if __name__ == "__main__":
    print("=== Pydantic Validation Layer ===\n")

    # --- VALID output (what Claude normally returns) ---
    print("Case 1: Valid AI output")
    valid_data = {"event_id": "EVT123", "title": "Team Kickoff", "location": "Room 4B", "attendees": 12, "confirmed": True}
    try:
        output = EventBookingOutput(**valid_data)
        print(f"  event_id  : {output.event_id}")
        print(f"  title     : {output.title}")
        print(f"  location  : {output.location}")
        print(f"  attendees : {output.attendees}")
        print(f"  confirmed : {output.confirmed}")
        print("  Result    : VALID\n")
    except Exception as e:
        print(f"  Result    : ERROR — {e}\n")

    # --- INVALID: extra field (Pydantic ignores by default — or raises with model_config) ---
    print("Case 2: AI returns extra unexpected field")
    extra_field_data = {"event_id": "EVT456", "title": "All Hands", "location": "Auditorium", "attendees": 80, "confirmed": False, "surprise_field": "something"}
    try:
        output = EventBookingOutput(**extra_field_data)
        print(f"  Output    : {output}")
        print("  Result    : Pydantic silently ignored the extra field (safe)\n")
    except Exception as e:
        print(f"  Result    : ERROR — {e}\n")

    # --- INVALID: business rule violation (lowercase event_id) ---
    print("Case 3: AI returns lowercase event_id (violates our business rule)")
    bad_id_data = {"event_id": "evt789", "title": "Sprint Review", "location": "Zoom", "attendees": 5, "confirmed": True}
    try:
        output = EventBookingOutput(**bad_id_data)
        print(f"  Output    : {output}\n")
    except Exception as e:
        print(f"  Result    : CAUGHT — {e}\n")

    # --- INVALID: out-of-range attendees ---
    print("Case 4: AI returns attendees=999 (exceeds max 500)")
    out_of_range = {"event_id": "EVT999", "title": "Conference", "location": "Main Hall", "attendees": 999, "confirmed": True}
    try:
        output = EventBookingOutput(**out_of_range)
        print(f"  Output    : {output}\n")
    except Exception as e:
        print(f"  Result    : CAUGHT — {e}\n")

    # --- LIVE CALL: extract from a real messy request ---
    print("Case 5: Live extraction from a messy natural language request")
    raw = "Please book the annual product review for next friday in the Berlin office, expecting around 35 people, all confirmed."
    try:
        booking = extract_event_details(raw)
        print(f"  event_id  : {booking.event_id}")
        print(f"  title     : {booking.title}")
        print(f"  location  : {booking.location}")
        print(f"  attendees : {booking.attendees}")
        print(f"  confirmed : {booking.confirmed}")
        print("  Result    : VALID — Pydantic typed object, ready to save to DB\n")
    except Exception as e:
        print(f"  Result    : ERROR — {e}\n")

    print("Key point: the Pydantic model IS the contract.")
    print("Bad data from the AI never reaches your database.")
