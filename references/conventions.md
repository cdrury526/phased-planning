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
`plan.json` owns lifecycle status, ordered phase IDs, dependencies, running phases, baseline evidence,
update date, and evidence references. `PLAN-STATUS.md` owns narrative handoff:
delivered behavior, verification results, blockers, unresolved decisions, next
action, and shelving reason. Do not maintain duplicate Markdown status tables.

Full phases (`type: "full"`, the default when omitted) have nonempty sections using the template's exact headings:
Objective, Scope, Out of scope, Prerequisites, Implementation steps,
Verification, Exit criteria, Completion evidence. Optional sections may be added.
Validation checks structure, not the quality of their contents.

## Ordering

Phase IDs start at `00` and increase sequentially, up to `99`. Filenames use
`PHASE-NN-lowercase-topic.md`. Dependencies may refer only to earlier phases.
In version 2, only the phases explicitly listed in `dependsOn` must be
complete before starting a phase. Independent tracks may run together. Numeric
order is the reading order, not an implicit dependency; requiring dependencies
to point backward keeps the graph acyclic. Shared-file conflicts and permission
to delegate remain the implementing agent's responsibility.

Version 1 plans retain sequential execution and singular `activePhase`. Do not
silently migrate existing plans or replace project schemas. To adopt version 2,
review the project schema, set `schemaVersion: 2`, replace `activePhase` with
`activePhases` (an array, empty when nothing is running), and review dependencies.
Scaffolding defaults to version 1 and remains compatible with v1-only project
schemas. Version 2 requires `--schema-version 2`; `--independent` and `--outline`
require that explicit opt-in. A v1-only schema rejects v2 requests until its
version 2 support is deliberately reviewed and merged, preserving project
constraints and validating existing plans. The scaffold never replaces it.

## Slice-driven execution

`plan.json` may declare `"execution": {"mode": "slices"}` (default `phase-doc`). The plan
remains the roadmap; a slice system does the execution. Each phase that has started names
its **epic slice** in `epicSlice` (repository-relative `.../slice.json`, `sliceType`
`epic-slice`); its child slices are planned in the phase document's **Planned slices**
section (which replaces Implementation steps) and scaffolded when the phase starts, with a
discovery slice first.

| Phase status | Epic slice |
| --- | --- |
| `pending` | none (optional; if set it must exist and be an epic) |
| `active` / `blocked` | required; not `done` or `cancelled` |
| `complete` | required; `done` (closed through the slice system) |

Evidence for a complete phase links the epic slice and the child slices' close records.
Slice statuses are owned by the slice system; the plan never duplicates them. The
checker reads only the epic slice's `sliceType` and `status`.

## Baseline work and outlines

Version 2 optionally records work completed before planning in `baseline`:

```json
"baseline": [
  {"title": "Walking skeleton", "evidence": ["Commit abc123: boot and health check verified"]}
]
```

Use real artifact references or command/results, and summarize the delivered
behavior in the handoff. Baseline entries have no lifecycle and do not count as
planned phases; draft phases remain pending. Baseline evidence never bypasses
phase exit criteria or dependencies. If baseline work satisfies a prerequisite,
name that outcome in the phase's Prerequisites rather than inventing a phase ID.

An outline phase has `type: "outline"` and only three required sections:
Objective, Scope, Exit criteria. Include exclusions in Scope while outlining.
Outlines must stay pending with empty evidence. Before authorizing execution,
promote to `type: "full"`, add all eight sections, and review actionable steps,
prerequisites, exclusions, and verification. Do not mark an outline complete.

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

For version 2, `activePhases` lists exactly all active and blocked phase IDs.

| Initiative | Phase state | activePhases |
| --- | --- | --- |
| `draft` | All `pending`; baseline allowed | `[]` |
| `active` | At least one `active`; others may be blocked | All running IDs |
| `blocked` | At least one `blocked`, none active | All blocked IDs |
| `complete` | All `complete` | `[]` |
| `shelved` | No active or blocked phase; preserve completed phases | `[]` |

Every running or completed phase requires its declared dependencies complete.
Version 1 retains exactly one running phase and requires all earlier phases complete.

Completed phases need a nonempty manifest `evidence` array and actual supporting
results in their document. References can be a commit, artifact path, or a concise
command/result record. Do not fabricate a reference or include secrets. Check
every exit criterion; a checkbox or successful validator run alone is not proof.

When shelving, return any unfinished active/blocked phase to `pending` and record
partial progress, the reason, and resumption conditions in the handoff. Shelved
initiatives are historical, not automatic work queues. Resume when requested.

When completing a phase, activate a ready phase if its work is authorized; preserve any other
running phases. If no work is authorized or running, leave the initiative shelved with the handoff explaining the pause. An active
phase identifies the next authorized work; it does not claim implementation is
already complete. Mark the whole initiative complete only when all phases finish.

## Useful content

Exit criteria describe observable behavior. Verification names a check and its
expected result. Prerequisites include access and external dependencies, not just
phase IDs. Scope exclusions prevent a small phase from absorbing related work.
Handoffs name the next concrete action and enough context to avoid reconstructing
the conversation. Architectural decisions stay linked to their canonical source.
