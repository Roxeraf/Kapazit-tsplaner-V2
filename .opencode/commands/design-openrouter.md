```markdown
---
description: Develop and compare solution designs using the OpenRouter planning workflow without implementing
agent: architect-openrouter
---

# DESIGN — OpenRouter

Work strictly in DESIGN mode using the OpenRouter planning workflow.

Design possible solutions for:

$ARGUMENTS

The problem should already be sufficiently understood from discovery or from the supplied requirement.

Use repository evidence and the existing architecture.

Do NOT implement code.

Do NOT modify files.

Do NOT jump directly into detailed implementation tasks unless explicitly requested.

---

# Objective

Develop a technically and functionally sound target solution.

Compare meaningful alternatives where multiple valid approaches exist.

The goal is:

UNDERSTAND OPTIONS
→ COMPARE TRADE-OFFS
→ SELECT A DIRECTION

Implementation happens later.

---

# Evidence

Use:

- previous discovery findings if available
- `AGENTS.md`
- relevant `CONCEPT.md` sections
- `README.md`
- actual repository implementation
- `explorer-openrouter` when additional repository evidence is required

Do not redesign the application based only on generic best practices.

Existing architecture is the baseline.

---

# Design principles

Prefer solutions that:

- reuse existing project architecture
- preserve Source-of-Truth models
- minimize duplicated business logic
- respect existing frontend/backend boundaries
- respect migration policy
- avoid unnecessary dependencies
- are understandable and maintainable
- minimize regression risk
- allow incremental implementation where practical

Do not optimize only for fastest initial implementation.

Consider long-term maintainability and future extension.

---

# Solution options

Create alternatives only when they are meaningfully different.

Do not invent Option B merely to have multiple options.

For each meaningful option evaluate:

- functional approach
- architecture impact
- backend impact
- frontend impact
- data-model impact
- API impact
- migration impact
- integration impact
- implementation complexity
- operational complexity
- maintainability
- scalability
- regression risk
- benefits
- drawbacks

---

# Data model

Where relevant determine:

- whether current models are sufficient
- whether new entities or fields are necessary
- whether existing Source-of-Truth models can be reused
- persistence implications
- migration implications
- compatibility with existing data

Do not propose schema changes without a concrete functional reason.

---

# Backend

Where relevant evaluate:

- existing routers
- shared calculation modules
- service/data flow
- schemas
- API contracts
- integration boundaries
- error handling
- existing business logic

Respect the repository rule that cross-router business logic belongs in shared modules.

---

# Frontend

Where relevant evaluate:

- views
- components
- API client
- state flow
- persistence behavior
- existing styling
- interaction patterns
- German UI conventions

Reuse existing UI patterns before proposing new abstractions.

---

# API design

If an API change is required, define the conceptual contract:

- purpose
- data direction
- request/response responsibility
- compatibility considerations

Do not create detailed implementation code.

---

# Migration impact

If a design affects the schema:

explicitly describe migration requirements.

Respect:

- new Alembic revision per schema change
- historical revisions must not be renamed or removed
- destructive migration only with safe data conversion
- migration guard requirement

---

# Parallelization potential

While designing, identify whether the eventual implementation can contain independent workstreams.

Potential workstreams may include:

- backend
- frontend
- documentation
- isolated modules

A workstream is only parallelizable when:

- interfaces are sufficiently defined
- file ownership is separate
- one stream does not depend on unfinished work from another
- changes do not overlap tightly

Do not force parallelization.

---

# Decision criteria

Evaluate designs against:

1. functional correctness
2. architecture consistency
3. implementation complexity
4. maintainability
5. migration safety
6. regression risk
7. future extensibility
8. development effort
9. validation effort

---

# Required output

## Problem statement

Summarize the problem being solved.

## Design goals

Define what a good solution must achieve.

## Constraints

List relevant architecture and product constraints.

## Option A

### Approach

### Architecture impact

### Backend impact

### Frontend impact

### Data/API impact

### Migration impact

### Advantages

### Disadvantages

### Risks

### Parallelization potential

## Option B

Use this section only when a genuinely different alternative exists.

### Approach

### Architecture impact

### Backend impact

### Frontend impact

### Data/API impact

### Migration impact

### Advantages

### Disadvantages

### Risks

### Parallelization potential

Add further options only when they provide real value.

## Comparison

Compare the options directly.

## Recommendation

Recommend the preferred direction when enough evidence exists.

Explain why it best fits this repository.

## Open decisions

List decisions that still require user approval or business input.

## Next step

If a direction has been selected, recommend:

`/plan-openrouter`

Do NOT implement.
```
