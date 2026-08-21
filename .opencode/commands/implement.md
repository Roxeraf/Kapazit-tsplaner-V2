---
description: Run the complete engineering pipeline
agent: orchestrator
---

Implement the following requirement:

$ARGUMENTS

Use the mandatory complete engineering workflow:

EXPLORE
→ PLAN
→ BUILD
→ VERIFY
→ REVIEW
→ COMPLETE

Do not skip any phase.

The orchestrator must delegate each phase to the appropriate specialized agent.

Do not perform implementation work directly in the orchestrator.

Use expert escalation only after the normal fix loop fails according to the orchestrator rules.

At completion report:

- implemented behavior
- changed files
- validation results
- review result
- agents invoked
- remaining risks