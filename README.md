# phased-planning

Cursor/Claude skill for repository implementation plans: explicit phase dependencies, parallel tracks, baseline evidence, outline phases, insertion phases
(`06b`, `06c`), structured status, completion evidence, and session handoffs.

## Install

Symlink into your skills directory:

```bash
ln -sfn ~/projects/phased-planning ~/.claude/skills/phased-planning
# optional Cursor copy:
ln -sfn ~/projects/phased-planning ~/.cursor/skills/phased-planning
```

Optional slice-driven execution (`execution.mode: slices`, `scaffold-plan.py --execution slices`):
phases run through an epic slice plus child slices in a devops-slices-style slice system, and the
checker ties phase status to the epic slice. See SKILL.md → Slice-driven execution.

New scaffolds default to version 1: sequential phases and one active phase.
Version 2 is an explicit opt-in with `--schema-version 2`; `--independent` and
`--outline` require it. Review and merge version 2 support into existing project
schemas deliberately and validate existing plans before adopting new fields.
The scaffold never replaces a project schema.

## Validate

```bash
python3 scripts/check-plans.py --root /path/to/repo PLANS/my-initiative
```

Requires Python 3 and `jsonschema` (`pip install -r scripts/requirements.txt`).

Passing checks establish structure only. Review evidence, feasibility, and exit
criteria separately; a green check does not establish implementation completion.

Run regression tests with `python3 -m unittest discover -s tests`.

## Docs

- [SKILL.md](SKILL.md) — agent skill entrypoint
- [references/conventions.md](references/conventions.md) — layout, insertion phases, lifecycle
