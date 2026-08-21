```markdown
---
description: Understand a problem and the current system using the OpenRouter planning workflow without designing or implementing yet
agent: architect-openrouter
---

# DISCOVER — OpenRouter

Work strictly in DISCOVER mode using the OpenRouter planning workflow.

Analyze the following topic:

$ARGUMENTS

The goal is to understand the current situation before selecting or designing a solution.

Use repository evidence wherever useful.

Use the configured OpenRouter planning team.

Do NOT implement code.

Do NOT modify files.

Do NOT prematurely create a final implementation plan.

---

# Objective

Understand:

- how the relevant area currently works
- which modules and data flows are involved
- which constraints exist
- which documented business rules apply
- which technical debt or inconsistencies are relevant
- which questions remain unresolved

The purpose of DISCOVER is understanding, not solution selection.

---

# Repository analysis

Use repository evidence to investigate:

- current behavior
- existing implementation
- relevant frontend areas
- relevant backend areas
- relevant data models
- APIs and consumers
- dependencies
- architecture patterns
- validation practices
- relevant documentation
- known technical debt
- potential regression areas

Use `explorer-openrouter` when repository discovery is required.

Do not repeatedly scan the repository yourself when explorer findings are sufficient.

---

# Documentation

Use:

- `AGENTS.md`
- relevant sections of `CONCEPT.md`
- `README.md`
- actual source code

Do not load the complete `CONCEPT.md` unless necessary.

When documentation and implementation disagree, explicitly report the discrepancy.

`CONCEPT.md` is authoritative for documented architecture decisions.

---

# Business understanding

Identify:

- current domain behavior
- business rules already implemented
- assumptions embedded in the code
- missing or ambiguous product decisions

Do not invent missing business logic.

If repository evidence cannot resolve an ambiguity, identify it as an open question.

---

# Technical understanding

Determine where applicable:

- frontend flow
- backend flow
- data flow
- API flow
- persistence flow
- calculation flow
- external integrations
- migration implications
- shared logic
- Source-of-Truth models

Do not propose major architectural changes during DISCOVER.

---

# Open questions

Do not ask the user questions that repository evidence can answer.

First investigate.

Only surface questions when:

- a genuine business decision is missing
- several valid behaviors are possible
- user preference is required
- the current architecture does not determine the answer

Questions should be specific and decision-oriented.

---

# Required output

## Current situation

Describe how the relevant area currently works.

## Relevant architecture

Describe the affected modules, layers and data flows.

## Existing implementation

Reference the important implementation areas.

## Constraints

List technical and business constraints.

## Relevant documentation

Identify relevant rules from `AGENTS.md`, `CONCEPT.md` or `README.md`.

## Technical debt / inconsistencies

List relevant existing issues only when they affect the topic.

## Findings

Summarize the most important evidence.

## Open questions

List unresolved questions that genuinely require a decision.

## Possible directions

Briefly identify plausible directions.

Do NOT select a final solution unless the evidence makes one direction obviously necessary.

---

# Restrictions

Do NOT:

- edit application files
- implement features
- fix bugs
- create migrations
- change configuration
- create a final implementation task list
- make product decisions for the user
- perform unrelated repository analysis

Stay in DISCOVER mode.

The next possible workflow is:

`/design-openrouter`

when the problem is sufficiently understood.
```
