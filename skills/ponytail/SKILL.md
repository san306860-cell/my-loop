---
name: ponytail
description: Apply Ponytail when the user explicitly selects it, including its lite, full, or ultra mode. Reduce the total cost of understanding, changing, and verifying a solution while preserving the requested behavior. A ponytail comment or an ordinary coding task does not activate this skill.
license: MIT
---

# Ponytail

Use only for the task or scope the user selected. Default intensity is **full**; the user can choose `lite`, `full`, or `ultra`. Do not carry an active mode into unrelated work.

## Understand, then simplify

Read the affected code and trace the real data and control flow before choosing a solution. Correctness, the user's requested behavior, and existing project constraints are prerequisites. Simplicity means lower total understanding, change, and verification cost; line count, file count, and number of implementations are not independent scores.

Consider reuse in this order, then check semantic fit:

1. Does the code serve a current requirement? Omit speculative work.
2. Does the codebase already own this behavior? Reuse the correct boundary.
3. Can the standard library or native platform implement the required semantics?
4. Can an installed dependency do so without pushing complexity onto callers?
5. Otherwise write clear, cohesive code. Expand a one-liner when that makes it easier to inspect.

The order is a way to find good options, not a reason to accept incorrect edge behavior. Compare actual alternatives for material design choices; do not invent alternatives for routine edits.

## Boundaries and verification

- An interface with one implementation can be useful when it hides real complexity, owns changing knowledge, or isolates an external dependency. Remove pass-through layers that add navigation without reducing caller burden. Split or combine by responsibilities, ownership, and invariants.
- For a bug, inspect callers and related entry points. Fix a shared invariant at its owner; handle callers separately when their semantics differ. A short diff in the wrong place is not simpler.
- Preserve trust-boundary validation, error handling that prevents data loss, security, accessibility, and all requested behavior. Do not ship a reduced requirement and ask afterward whether the full request was wanted.
- Mark an actual deliberate limit with a `ponytail:` comment naming the limit and upgrade condition. Use the existing decision source for accepted limits; seek a new decision only when the unresolved choice changes goals, key behavior, or authorization.
- Choose checks that can catch the relevant failure. Reuse applicable evidence and existing tests. Add a check when it provides missing protection, not merely because a branch or loop exists; routine low-impact changes can use direct inspection. Recheck when related code, dependencies, environment, or unresolved concerns change.

## Intensity

| Mode | Emphasis |
|---|---|
| lite | Explain a simpler alternative when there is a meaningful trade-off. |
| full | Use the least complex implementation that satisfies the task and its constraints. |
| ultra | Scrutinize speculative work and unused machinery more aggressively, while completing the authorized requirement. |

## Handoff

Follow the active workflow's evidence and reporting requirements. In my-loop, keep actual design choices and evidence in the worker receipt for reviewer verification; do not replace it with a code-only response. Elsewhere, explain the result and any material trade-off concisely, with enough evidence to assess it. No fixed line count, forced comparison, or extra report is required.
