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

New scaffolds use version 2. The checker also preserves version 1 lifecycle rules;
upgrade existing project schemas deliberately before adopting new fields.

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
