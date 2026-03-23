# Wall 3: Consistency Crisis

## The Problem

A vague or absent system prompt leaves the model free to improvise.
In a customer support context, improvisation means:

- Wildly different tones across sessions (apologetic vs. dismissive)
- Invented policies that contradict your real terms of service
- Inconsistent escalation paths that confuse both customers and agents
- No predictable behaviour you can test or reason about

Users who ask "Can I get a refund?" on Monday and Tuesday should get
the same answer. With a generic prompt, they won't.

## The Progression

### 1. `generic_assistant.py` — Improvisation at its worst
System prompt: `"Be helpful."` Three simulated responses to the same
refund question show: an over-promising response, a useless brush-off,
and a confident-sounding response that invents policies wholesale.
A live call at the end shows this happens in real usage too.

### 2. `role_based_system.py` — The three-layer system prompt
A structured system prompt with three mandatory sections:

| Layer | Purpose | Example |
|-------|---------|---------|
| IDENTITY | Anchors persona and tone | "You are Alex, a customer support specialist for TechCorp…" |
| CONSTRAINTS | Explicit must/must-not rules | "Never promise refunds outside the 30-day window. Always escalate billing disputes." |
| CONTEXT | Ground-truth facts the model may cite | Return policy, known issues, escalation email, SLA details |

The same three questions now get consistent, policy-compliant answers
every time because the model can only cite what is explicitly in CONTEXT.

### 3. `consistency_testing.py` — Prove it with measurement
Ship nothing without testing it. `test_consistency()` sends the same
question N times and scores each response against a set of assertions:

- Does the response mention the 30-day policy?
- Does it include the escalation email for billing disputes?
- Does it invent numbers not in the system prompt?
- Does it end with a clear next step?

Each assertion gets a consistency score (0-100%). A score below 90%
means the system prompt is fragile on that dimension and needs tightening
before the feature goes live.

## Key Takeaway

Vague prompts → improvised behaviour → inconsistent support → user mistrust.
Three-layer prompts (Identity + Constraints + Context) → predictable, testable,
policy-grounded behaviour → something you can actually ship with confidence.
