````markdown
---
description: Convert an approved design into a concrete implementation plan using the OpenRouter planning workflow
agent: architect-openrouter
---

# IMPLEMENTATION PLAN — OpenRouter

Work strictly in IMPLEMENTATION PLAN mode using the OpenRouter planning workflow.

Create an actionable engineering plan for:

$ARGUMENTS

Use the approved design direction from the current conversation when available.

Use repository evidence.

Do NOT implement code.

Do NOT modify application files.

The result must be suitable as direct input for the engineering implementation workflow.

---

# Objective

Translate the approved solution into:

- clear implementation scope
- coherent engineering tasks
- explicit dependencies
- acceptance criteria
- validation strategy
- safe parallelization opportunities

The plan must be concrete enough that implementation agents do not need to invent missing architecture.

---

# Evidence

Use:

- approved design decisions
- discovery findings
- `AGENTS.md`
- relevant sections of `CONCEPT.md`
- `README.md`
- actual repository structure
- `explorer-openrouter` if additional repository evidence is necessary

Do not plan against imaginary files or architecture.

---

# Scope definition

Explicitly define:

## In scope

What this implementation will deliver.

## Out of scope

What will deliberately not be changed.

Avoid scope creep.

---

# Current behavior

Describe the relevant existing behavior.

---

# Desired behavior

Describe the expected final functional behavior.

---

# Architecture decision

State the chosen design approach.

Explain the important architecture implications.

Do not reopen already approved design decisions unless repository evidence shows a conflict.

---

# Affected architecture

Determine applicable areas:

- frontend
- backend
- data model
- API
- migrations
- calculations/business logic
- integrations
- export
- documentation

List only relevant areas.

---

# Backend plan

Where applicable describe:

- affected routers
- shared modules
- schemas
- models
- calculation logic
- services/integrations
- API behavior
- persistence behavior

Respect existing repository architecture.

---

# Frontend plan

Where applicable describe:

- affected views
- components
- API-client changes
- types
- state/data flow
- user interaction
- visual behavior
- validation requirements

Keep UI language and existing project conventions consistent.

---

# Data-model plan

Where applicable describe:

- models affected
- new fields/entities
- changed relationships
- Source-of-Truth implications
- data compatibility
- migration requirements

Do not create schema changes without a clear requirement.

---

# API plan

Where applicable define:

- affected endpoint(s)
- request responsibility
- response responsibility
- payload/type changes
- compatibility impact
- frontend consumers

API contracts must be sufficiently clear before frontend/backend work is marked parallelizable.

---

# Migration plan

Where schema changes exist define:

- required Alembic revision
- data transformation
- compatibility concerns
- migration ordering
- migration validation

Required validation:

`python backend/check_migrations.py`

---

# Documentation impact

Determine whether the implementation requires changes to:

- `CONCEPT.md`
- `README.md`

Do not require documentation changes for trivial implementation details.

---

# Task decomposition

Break the implementation into coherent engineering tasks.

Do not create one oversized task when meaningful independent boundaries exist.

Each task must use the following structure.

## TASK-XX — Task name

### Objective

Describe the outcome of this task.

### Scope

Describe exactly what belongs to this task.

### Out of scope

Describe relevant exclusions.

### Affected files/modules

List likely areas.

### Dependencies

List prerequisite tasks or contracts.

### Implementation

Describe the required engineering steps.

### Acceptance criteria

Create concrete, verifiable criteria.

### Validation

Describe the validation required for this task.

### Execution mode

Set exactly one:

`SEQUENTIAL`

or:

`PARALLELIZABLE`

### Parallelization reason

If PARALLELIZABLE, explain:

- which other tasks it can run alongside
- why file ownership does not conflict
- which interfaces must already be stable

If SEQUENTIAL, explain the dependency when relevant.

---

# Dependency graph

Create a readable dependency graph.

Example:

```text
TASK-01
   │
   ├── TASK-02
   │
   └── TASK-03
          │
          ▼
       TASK-04
````

Use the actual plan dependencies.

---

# Parallel workstreams

Identify safe parallel groups.

Example:

```text
Wave 1
→ TASK-01

Wave 2 — parallel
→ TASK-02 Backend
→ TASK-03 Frontend
→ TASK-04 Documentation

Wave 3
→ TASK-05 Integration / Validation
```

Only mark tasks parallel when:

* file ownership does not overlap
* interfaces are stable
* dependencies are satisfied
* independent validation is possible

Do not claim that parallel execution is safe merely because tasks are in different layers.

---

# Integration strategy

For parallel workstreams define:

* expected integration point
* shared contracts
* ownership boundaries
* final integrated validation

The tester must validate the integrated repository state after workstreams finish.

---

# Validation strategy

Define proportional gates.

Frontend where applicable:

* `npm.cmd run lint`
* `npm.cmd run build`
* targeted UI/browser validation

Backend where applicable:

* relevant import/start smoke
* API/curl validation

Schema where applicable:

* `python backend/check_migrations.py`
* relevant backend verification

Full-stack where applicable:

* integrated backend/frontend verification

Do not introduce a new testing framework without an explicit project decision.

---

# Risks

Identify relevant:

* functional risk
* architecture risk
* migration risk
* regression risk
* data integrity risk
* API compatibility risk
* concurrency/state risk
* integration risk
* deployment/setup risk

For each meaningful risk describe mitigation.

---

# Overall acceptance criteria

Define the conditions under which the complete feature can be considered delivered.

These must be testable or verifiable.

---

# Implementation readiness

At the end classify the plan as exactly one:

`READY_FOR_IMPLEMENTATION`

`DECISIONS_REQUIRED`

`TASK_DECOMPOSITION_REQUIRED`

Use:

READY_FOR_IMPLEMENTATION
when architecture, scope and dependencies are sufficiently defined.

DECISIONS_REQUIRED
when business or architecture decisions are still missing.

TASK_DECOMPOSITION_REQUIRED
when the supplied scope is still too large or incoherent.

---

# Handoff

If READY_FOR_IMPLEMENTATION:

provide the recommended execution order.

Example:

```text
/implement TASK-01 ...
```

Then subsequent tasks according to the dependency graph.

For parallelizable tasks explicitly identify which tasks may be started together.

Do NOT implement code yourself.

```
```
