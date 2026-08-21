---
description: Fast path for small, low-risk code changes
agent: builder
---

# QUICK Engineering Workflow

Implement the following small, low-risk change:

$ARGUMENTS

This command is the fast path for small and clearly scoped engineering tasks.

The goal is to complete trivial changes quickly and cost-efficiently without
running the full multi-agent engineering pipeline.

---

# 1. QUICK SUITABILITY GATE

Before modifying any files, determine whether the requested task is suitable
for the QUICK workflow.

QUICK is suitable for changes such as:

- wording changes
- labels
- small UI text changes
- simple CSS adjustments
- small visual corrections
- tiny configuration changes
- obvious one-file bug fixes
- very small local refactors
- simple changes with clearly understood behavior
- changes with no architectural impact

QUICK is NOT suitable if the task involves:

- database schema changes
- Alembic migrations
- new APIs or API contracts
- major backend logic
- business-critical logic
- cross-module architecture changes
- authentication or authorization
- security-sensitive behavior
- new dependencies
- large refactoring
- unclear requirements
- multiple architectural layers
- complex state management
- significant data-model changes
- changes with difficult-to-estimate regression risk
- changes requiring architectural decisions

If the task is NOT suitable for QUICK:

DO NOT modify any files.

Return:

QUICK_NOT_SUITABLE

Then explain briefly:

- why the task is not suitable for QUICK
- which areas appear to be affected
- why the full engineering workflow is recommended

Recommend:

/implement $ARGUMENTS

Stop immediately after this recommendation.

Do not attempt a partial implementation.

---

# 2. INSPECT

If the task passes the QUICK suitability gate:

Inspect only the repository areas necessary to perform the requested change.

You may use:

- read
- glob
- grep
- bash

Keep repository exploration focused.

Do not perform broad repository analysis unless required to understand the
requested change.

Before editing, confirm:

- the correct file has been identified
- the existing behavior is understood
- the requested change is locally scoped
- no architectural changes are required

If inspection reveals that the task is more complex than initially expected:

STOP.

Return:

QUICK_NOT_SUITABLE

and recommend the full `/implement` workflow.

---

# 3. IMPLEMENT

Make the smallest coherent change necessary to satisfy the requirement.

Rules:

- modify only files necessary for the task
- preserve existing architecture
- preserve existing project conventions
- reuse existing patterns
- avoid unrelated refactoring
- avoid unnecessary abstractions
- do not introduce new dependencies
- do not change architecture
- do not modify unrelated behavior
- do not rename internal identifiers unless explicitly requested
- do not change API contracts unless explicitly requested
- do not change database schemas
- do not create migrations
- do not weaken existing validation
- do not remove existing error handling
- do not silently expand the scope of the task

For GUI wording changes:

- change only visible user-facing text
- preserve component names
- preserve filenames
- preserve imports
- preserve routes
- preserve internal identifiers

unless the requirement explicitly asks for those to be renamed.

---

# 4. DIFF REVIEW

After implementation, inspect the resulting diff.

Verify:

- only intended files changed
- only intended behavior changed
- no unrelated formatting changes occurred
- no accidental code changes occurred
- no unnecessary refactoring occurred

If unexpected changes are present, correct them before validation.

---

# 5. VALIDATE

Run the smallest relevant validation for the affected area.

For frontend changes, where available, prefer:

npm.cmd run lint

and:

npm.cmd run build

Use `npm.cmd` on Windows if PowerShell execution policy prevents `npm.ps1`
from running.

For other small changes:

- use existing project validation commands
- prefer targeted validation where possible
- do not invent validation commands
- do not modify unrelated code to make validation pass

If validation produces existing warnings unrelated to the change:

- report them separately
- do not fix them unless explicitly requested

If validation fails because of the implementation:

Attempt to fix the implementation.

Maximum QUICK fix attempts: 2.

After each fix:

1. inspect the change
2. rerun the relevant validation

If the task cannot be completed successfully after 2 fix attempts:

STOP.

Return:

QUICK_FAILED

Report:

- failing validation
- actual error
- suspected root cause
- attempted fixes
- affected files

Recommend continuing with:

/implement $ARGUMENTS

Do not continue an open-ended debugging loop.

---

# 6. SCOPE ESCALATION

At ANY point during QUICK, if you discover that the task requires:

- architectural decisions
- changes across multiple architectural layers
- significant backend changes
- database changes
- API design changes
- security-sensitive changes
- large refactoring
- extensive debugging
- unclear business behavior

STOP the QUICK workflow.

Do not continue implementing.

Return:

QUICK_NOT_SUITABLE

Explain the discovered complexity and recommend:

/implement $ARGUMENTS

---

# 7. COMPLETE

A QUICK task is complete only when:

- the requested change has been implemented
- the diff contains only intended changes
- relevant validation has passed
- no known regression was introduced

Return the following completion report:

## Implemented

Briefly describe what was changed.

## Changed files

List all modified files and briefly explain each change.

## Validation

List the validation commands that were executed and their results.

Separate:

- errors
- warnings
- pre-existing warnings

## Scope

Confirm that the task remained within QUICK scope.

## Remaining risks

List any remaining risks.

If none are known, state:

No known risks introduced by this change.

---

# QUICK PRINCIPLE

QUICK prioritizes:

speed
+ low cost
+ minimal changes
+ targeted validation

It does NOT replace the full engineering workflow.

When in doubt whether a task is trivial or complex:

prefer `/implement`.