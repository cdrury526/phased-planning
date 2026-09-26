---
name: phased-planning
description: Create, update, resume, or validate repository implementation plans with ordered phases, structured status, completion evidence, and session handoffs. Use for persistent multi-phase planning or requests for plan templates and schemas; not for ordinary fixes or a brief conversational plan.
---

# Phased planning

Build plans another coding agent can resume from files alone. This skill uses
plain Markdown, JSON Schema, and a Python checker; no particular agent runtime,
connector, cloud service, or project architecture is required.

If this file is loaded through a symlink (including a standalone `.md` skill),
resolve its real filesystem path first. Resolve all resource links and
`SKILL_DIR` relative to the real SKILL.md's parent, not the symlink directory.

## Fit the repository first

Read applicable repository instructions and the architecture/requirements source
of truth. Inspect existing plans before creating files. Repository rules and the
user's requested format take precedence over these defaults. Do not migrate an
existing planning system just to match this skill. For an incompatible format,
use its own validator and apply the useful handoff/evidence practices here.

Create persistent plan files when the user requests a plan or repository rules
require them. A request to plan does not authorize implementation. A request to
resume implementation uses the existing authorized phases; it is not a reason to
create another initiative. Follow the repository's commit/push policy; this
skill does not impose one globally.

## Create a plan

Read [conventions](references/conventions.md) for layout and lifecycle rules.

1. Choose a descriptive lowercase kebab-case initiative name and run the
   scaffold command below. It copies [the templates](assets/_template), fills
   names and today's local date, and refuses existing destinations.
2. The script copies [the schema](assets/plan.schema.json) only if absent and
   validates against an existing project schema before writing project files.
   Inspect incompatible schemas instead of replacing them to make it pass.
3. Fill every full-phase template prompt with project-specific content. Set manifest `id`
   to the directory name and `updatedAt` to today's actual date. Rename and
   duplicate phase documents as needed; align IDs, filenames, and index links.
4. Split at independently verifiable outcomes. Include prerequisites, scope
   exclusions, actionable steps, concrete checks with expected results, and
   observable exit criteria. Avoid speculative later features. Reference
   architectural decisions rather than creating a competing source of truth.
5. Record already delivered work with actual evidence in version 2 `baseline`;
   use pending `outline` phases for later work and promote them to full documents
   before starting.
6. Leave newly authored plans `draft` with pending phases unless implementation
   is also authorized and actually starting. Document unresolved questions in
   the handoff without inventing answers or completion evidence.
7. Validate and review the resulting plan. Report its location and unresolved
   decisions. Creating a plan does not itself meet any implementation exit criteria.

The template assets are intended to be copied and filled, not treated as tasks.
Do not install Git hooks, edit global agent settings, or copy this whole skill
into a project merely to use it. If repository-local templates or tooling are
requested, copy the relevant assets and adapt the checker paths deliberately.

### Scaffold command

Resolve `SKILL_DIR` to this skill's real directory, then run:

```bash
python3 "$SKILL_DIR/scripts/scaffold-plan.py" my-initiative \
  --root /absolute/path/to/repository \
  --title "My initiative" \
  --phase foundation --phase delivery
```

`--root` defaults to the current directory. Omit `--phase` to create one
`foundation` phase; repeat it for ordered phases, each depending on its predecessor by default. Use `--independent` for no initial
dependencies and edit `dependsOn` for mixed tracks. Use `--outline delivery` to
create a lightweight pending outline for that named phase. New scaffolds use
version 2; existing project schemas are never upgraded automatically.
The script uses Python and the validator dependency described below. It creates
only `PLANS/<initiative>/` and the schema when missing. It does not install hooks,
project scripts, or global settings. An existing destination is an error, even
if identical; edit that plan directly. It never starts implementation.

Generated files pass structural validation but still contain authoring prompts.
Complete them from the user's request, then validate again and review exit criteria.

## Resume and hand off

Read the initiative's `plan.json`, `PLAN-STATUS.md`, and running phases (`activePhases` in version 2, `activePhase` in version 1). Open other
phases only as needed to resolve dependencies or blockers. Verify prerequisites
before advancing. During implementation, stay within authorized phases and verify explicit dependencies.

Record partial progress and blockers honestly. Before marking a phase complete,
check each exit criterion against actual evidence, then update the phase evidence,
manifest, and handoff together. Use the repository's prescribed checks rather than
adding a test suite by default. Update status and the next concrete action at
session end; read-only questions need no artificial edits.

## Validate

Prefer the repository's checker when one exists. Otherwise run this skill's
checker. Resolve `SKILL_DIR` to the directory containing this SKILL.md using the
agent's available filesystem/shell tools; do not assume the current directory is
the skill directory.

```bash
python3 "$SKILL_DIR/scripts/check-plans.py" --root /absolute/path/to/repository
# Or validate a single initiative (relative paths resolve against --root):
python3 "$SKILL_DIR/scripts/check-plans.py" --root /absolute/path/to/repository PLANS/my-initiative
```

Requires Python 3 and `jsonschema`. If missing, install the declared dependency
into an isolated environment outside the repository, following environment policy:

```bash
python3 -m venv /tmp/phased-planning-tools
/tmp/phased-planning-tools/bin/pip install -r "$SKILL_DIR/scripts/requirements.txt"
/tmp/phased-planning-tools/bin/python "$SKILL_DIR/scripts/check-plans.py" --root /absolute/path/to/repository
```

The checker uses the repository's `PLANS/plan.schema.json` when present, otherwise
the bundled schema. It is intended for this skill's plan format, not arbitrary
schemas. Missing files, lifecycle inconsistencies, invalid dependencies, empty
required sections, and absent completion evidence fail validation. If execution
or dependency installation is unavailable, perform a manual review and state
that automated validation was not run.

Schema success proves structure, not that evidence is truthful or criteria are
satisfied. Review those judgments before advancing. Templates deliberately contain
authoring prompts: replace them in real plans even though they can pass validation.
