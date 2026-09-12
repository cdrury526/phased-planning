# Plan format and lifecycle

Use this layout for new initiatives when the repository has no competing format:

```text
PLANS/
  plan.schema.json
  <initiative>/
    README.md
    plan.json
    PLAN-STATUS.md
    PHASE-00-foundation.md
    PHASE-01-delivery.md
```

`README.md` states the outcome and links to phase documents in manifest order.
`plan.json` owns lifecycle status, ordered phase IDs, dependencies, current phase,
update date, and evidence references. `PLAN-STATUS.md` owns narrative handoff:
delivered behavior, verification results, blockers, unresolved decisions, next
action, and shelving reason. Do not maintain duplicate Markdown status tables.

Every phase has nonempty sections using the template's exact headings:
Objective, Scope, Out of scope, Prerequisites, Implementation steps,
Verification, Exit criteria, Completion evidence. Optional sections may be added.
Validation checks structure, not the quality of their contents.

## Ordering

Phase IDs start at `00` and increase sequentially, up to `99`. Filenames use
`PHASE-NN-lowercase-topic.md`. Dependencies may refer only to earlier phases.
All earlier phases must be complete before a phase starts, including when
`dependsOn` is empty. This default is sequential; it is not a parallel work graph.
If a project needs parallel phases, follow its existing rules or explicitly
adapt the format and validator within the requested scope.

### Insertion phases (plan deviations)

When work was left out of the original plan, add an **insertion** phase after its
base phase and before the next base number:

| Pattern | Example | Document |
|---|---|---|
| Base | `06` | `PHASE-06-embed.md` |
| Insertion | `06b`, `06c`, … | `PHASE-06b-signing-ui.md` |

Rules:

- Insertion ID = two-digit base + lowercase suffix (`06b`, not `6b` or `06-b`).
- Document filename must be `PHASE-{id}-topic.md` (id includes suffix).
- List insertions **immediately after** their base phase in `plan.json` (before the
  next base number). Example order: `05`, `06`, `06b`, `07`.
- `dependsOn` may reference the base phase or earlier; default depends on base when
  the insertion is a refinement (e.g. `06b` depends on `06`).
- Do not renumber completed base phases — insertions document discovered scope, not
  replanning from scratch.

## Status transitions

| Initiative | Phase state | activePhase |
| --- | --- | --- |
| `draft` | All `pending` | `null` |
| `active` | Exactly one `active`; earlier phases complete | Current phase ID |
| `blocked` | Exactly one `blocked`; earlier phases complete | Blocked phase ID |
| `complete` | All `complete` | `null` |
| `shelved` | No active or blocked phase; preserve completed phases | `null` |

Completed phases need a nonempty manifest `evidence` array and actual supporting
results in their document. References can be a commit, artifact path, or a concise
command/result record. Do not fabricate a reference or include secrets. Check
every exit criterion; a checkbox or successful validator run alone is not proof.

When shelving, return any unfinished active/blocked phase to `pending` and record
partial progress, the reason, and resumption conditions in the handoff. Shelved
initiatives are historical, not automatic work queues. Resume when requested.

When completing a phase, activate the next phase if its work is authorized, or
leave the initiative shelved with the handoff explaining the pause. An active
phase identifies the next authorized work; it does not claim implementation is
already complete. Mark the whole initiative complete only when all phases finish.

## Useful content

Exit criteria describe observable behavior. Verification names a check and its
expected result. Prerequisites include access and external dependencies, not just
phase IDs. Scope exclusions prevent a small phase from absorbing related work.
Handoffs name the next concrete action and enough context to avoid reconstructing
the conversation. Architectural decisions stay linked to their canonical source.
