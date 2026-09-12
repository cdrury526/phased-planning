# phased-planning

Cursor/Claude skill for repository implementation plans: ordered phases, insertion phases
(`06b`, `06c`), structured status, completion evidence, and session handoffs.

## Install

Symlink into your skills directory:

```bash
ln -sfn ~/projects/phased-planning ~/.claude/skills/phased-planning
# optional Cursor copy:
ln -sfn ~/projects/phased-planning ~/.cursor/skills/phased-planning
```

Set `PHASED_PLANNING_SKILL_DIR=~/projects/phased-planning` when using `mw plan review`.

## Validate

```bash
python3 scripts/check-plans.py --root /path/to/repo PLANS/my-initiative
```

Requires Python 3 and `jsonschema` (`pip install -r scripts/requirements.txt`).

## Docs

- [SKILL.md](SKILL.md) — agent skill entrypoint
- [references/conventions.md](references/conventions.md) — layout, insertion phases, lifecycle
