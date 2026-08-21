---
description: Execute a small low-risk engineering change through the OpenRouter fallback workflow
agent: orchestrator-openrouter
---

# QUICK — OpenRouter

Execute the following requirement using the OpenRouter QUICK engineering workflow:

$ARGUMENTS

This command is intended for small, clear and low-risk changes when the
OpenCode Go provider is unavailable or its usage limit has been reached.

Use only the configured OpenRouter engineering agents.

---

# Workflow

Use:

QUICK
→ INSPECT
→ IMPLEMENT
→ DIFF REVIEW
→ TARGETED VALIDATION
→ COMPLETE

The implementation must be delegated to:

@builder-openrouter

Do not use the full IMPLEMENT pipeline unless QUICK is determined to be unsafe.

---

# QUICK eligibility

QUICK is appropriate only when ALL of the following are true:

- the requirement is clear
- the expected change is small
- the change is locally scoped
- regression risk is low
- no architectural decision is required
- no database/schema change is required
- no Alembic migration is required
- no API contract change is required
- no new dependency is required
- no security-sensitive behavior is involved
- no substantial business logic is changed
- no complex state-management change is required

Typical QUICK tasks include:

- GUI wording
- labels
- small CSS adjustments
- minor visual corrections
- tiny configuration changes
- obvious local bugs
- small local refactors
- simple text changes

---

# Implementation

Invoke:

@builder-openrouter

Provide:

- the original requirement
- instruction that this is a QUICK task
- requirement to make the smallest coherent change
- requirement to inspect existing repository state
- requirement to preserve existing user changes
- requirement to inspect the final diff
- requirement to run proportional targeted validation

The orchestrator must not modify files itself.

---

# Repository safety

Before modifying files the builder must:

1. inspect the relevant implementation
2. inspect repository state
3. identify existing uncommitted changes
4. preserve existing user changes
5. determine the smallest required change

Existing uncommitted changes may belong to the user.

Never automatically:

- reset
- restore
- discard
- clean
- overwrite
- stash

existing changes.

Do not automatically:

- commit
- push
- merge
- rebase
- create a pull request

unless explicitly requested.

---

# Scope discipline

The builder must modify only what is necessary for the requested QUICK change.

Do not perform:

- unrelated cleanup
- unrelated refactoring
- speculative improvements
- architecture redesign
- mass renaming
- formatting-only changes outside the affected scope

Prefer:

smallest coherent change
→ targeted validation
→ done

---

# Validation

Validation must be proportional to the actual change.

For frontend changes where applicable:

npm.cmd run lint
npm.cmd run build

For very small GUI/text changes, use the relevant repository validation gates
without introducing unnecessary additional testing.

For backend changes use relevant existing smoke/API validation.

Do not introduce a new testing framework.

---

# QUICK escalation

If @builder-openrouter discovers any of the following:

- database impact
- schema impact
- migration requirement
- API contract impact
- architecture impact
- multiple tightly coupled layers
- unclear business behavior
- high regression risk
- unexpected implementation complexity
- broad refactor requirement

the builder must stop and return:

QUICK_NOT_SUITABLE

Do not improvise a larger implementation inside QUICK.

When QUICK_NOT_SUITABLE is returned:

stop the QUICK workflow.

Recommend:

/implement-openrouter <original requirement>

The complete OpenRouter engineering pipeline should then handle the task.

---

# Completion criteria

QUICK is complete only when:

- the requested change was implemented
- the final diff contains only relevant changes
- existing user changes were preserved
- targeted validation passed
- no known new regression was introduced

A separate tester and reviewer are intentionally not required for a normal
successful QUICK task.

---

# Required final report

Return:

## Workflow

QUICK

## Provider

OpenRouter fallback

## Implemented

Describe exactly what changed.

## Changed files

List modified files and their purpose.

## Validation

List validation actually executed and its result.

## Review

State:

Full independent tester/reviewer pipeline intentionally skipped because this
was a QUICK task.

## Agent used

builder-openrouter

## Remaining risks

List known risks.

If none are known, state that no known new risks were introduced.

---

# Restrictions

Do NOT:

- invoke the normal Go builder
- use OpenCode Go agents
- invoke expert-openrouter for a normal QUICK task
- silently expand QUICK into a large implementation
- skip validation
- claim validation that was not actually executed

If the task exceeds QUICK boundaries, escalate to:

/implement-openrouter