---
description: Convert an approved design into a concrete implementation plan
agent: architect
---

Work strictly in IMPLEMENTATION PLAN mode.

Create an actionable engineering plan for:

$ARGUMENTS

Use:

- repository evidence
- existing architecture
- AGENTS.md
- relevant CONCEPT.md sections
- previously approved design decisions if available in the conversation

Do NOT implement code.

Return:

## Objective

## Scope

## Out of scope

## Approved design

## Current behavior

## Desired behavior

## Affected modules

## Backend changes

## Frontend changes

## Data-model changes

## API changes

## Migration requirements

## Documentation impact

## Implementation tasks

For every task include:

- Task ID
- objective
- scope
- affected files/modules
- dependencies
- acceptance criteria
- validation
- execution mode: SEQUENTIAL or PARALLELIZABLE

## Dependency graph

Show which tasks depend on others.

## Parallel workstreams

Identify tasks that may safely run concurrently.

## Risks

## Overall acceptance criteria

## Validation strategy

The final result must be suitable as input for the `/implement` workflow.