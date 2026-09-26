#!/usr/bin/env python3
"""Create a draft initiative from bundled templates, without overwriting files."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SKILL_ROOT = Path(__file__).resolve().parents[1]


def slug(value):
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", value):
        raise argparse.ArgumentTypeError("use lowercase kebab-case, starting with a letter")
    return value


def title_for(value):
    return value.replace("-", " ").capitalize()


def populate(directory, name, title, phases, independent=False, outlines=(), schema_version=1):
    shutil.copytree(SKILL_ROOT / "assets/_template", directory)
    manifest = directory / "plan.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.update(id=name, title=title, updatedAt=date.today().isoformat())
    data["schemaVersion"] = schema_version
    if schema_version == 1:
        data.pop("activePhases", None)
        data.pop("baseline", None)
        data["activePhase"] = None
    else:
        data.pop("activePhase", None)
        data["activePhases"] = []
        data["baseline"] = []
    data["phases"] = []
    phase_template = directory / "PHASE-00-foundation.md"
    phase_text = phase_template.read_text(encoding="utf-8")
    phase_template.unlink()
    outline_text = (SKILL_ROOT / "assets/outline-phase.md").read_text(encoding="utf-8")
    links = []
    for index, phase in enumerate(phases):
        phase_id = f"{index:02d}"
        phase_title = title_for(phase)
        filename = f"PHASE-{phase_id}-{phase}.md"
        (directory / filename).write_text(
            (outline_text if phase in outlines else phase_text).replace("# Phase 00 — Foundation", f"# Phase {phase_id} — {phase_title}", 1),
            encoding="utf-8",
        )
        data["phases"].append({
            "id": phase_id, "title": phase_title, "document": filename,
            "status": "pending", "dependsOn": [f"{index - 1:02d}"] if index and not independent else [],
            "evidence": [],
        })
        if schema_version == 2:
            data["phases"][-1]["type"] = "outline" if phase in outlines else "full"
        links.append(f"{index + 1}. [{phase_id} — {phase_title}]({filename})")
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    readme = directory / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        .replace("# Initiative title", f"# {title}", 1)
        .replace("1. [00 — Foundation](PHASE-00-foundation.md)", "\n".join(links)),
        encoding="utf-8",
    )
    handoff = directory / "PLAN-STATUS.md"
    handoff.write_text(
        handoff.read_text(encoding="utf-8").replace("# Initiative handoff", f"# {title} — Handoff", 1),
        encoding="utf-8",
    )


def scaffold(args):
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--root must be an existing project directory")
    plans = root / "PLANS"
    if plans.is_symlink() or (plans.exists() and not plans.is_dir()):
        raise ValueError("PLANS must be a regular directory, not a file or symlink")
    destination = plans / args.name
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"destination already exists; refusing to overwrite: {destination}")
    schema = plans / "plan.schema.json"
    if schema.is_symlink() or (schema.exists() and not schema.is_file()):
        raise ValueError("existing schema must be a regular file")

    # Validate against the actual project schema before writing into the project.
    with tempfile.TemporaryDirectory(prefix="phased-plan-scaffold-") as temporary:
        staged_root = Path(temporary)
        staged_plans = staged_root / "PLANS"
        staged_plans.mkdir()
        staged = staged_plans / args.name
        populate(staged, args.name, args.title or title_for(args.name), args.phase or ["foundation"], args.independent, args.outline, args.schema_version)
        schema_bytes = (schema if schema.exists() else SKILL_ROOT / "assets/plan.schema.json").read_bytes()
        (staged_plans / "plan.schema.json").write_bytes(schema_bytes)
        result = subprocess.run([
            sys.executable, str(SKILL_ROOT / "scripts/check-plans.py"),
            "--root", str(staged_root), f"PLANS/{args.name}",
        ], capture_output=True, text=True)
        if result.returncode:
            if args.schema_version == 2 and schema.exists():
                raise ValueError(
                    f"Existing project schema {schema} rejected the version 2 plan. "
                    f"To opt in deliberately, review and merge version 2 support from "
                    f"{SKILL_ROOT / 'assets/plan.schema.json'} into the project schema, "
                    "validate existing plans, then retry with --schema-version 2. "
                    "The schema was not replaced and project files were not written.\n"
                    + result.stderr
                )
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

        plans.mkdir(exist_ok=True)
        # Exclusive creation also protects against another invocation racing us.
        destination.mkdir()
        created_schema = False
        try:
            if not schema.exists():
                with schema.open("xb") as output:
                    created_schema = True
                    output.write(schema_bytes)
            elif schema.is_symlink() or schema.read_bytes() != schema_bytes:
                raise ValueError("project schema changed during scaffolding; retry after reviewing it")
            for source in staged.iterdir():
                with (destination / source.name).open("xb") as output:
                    output.write(source.read_bytes())
        except Exception:
            shutil.rmtree(destination)
            if created_schema:
                schema.unlink()
            raise
    print(f"Created and structurally validated {destination}")
    print("Draft only: fill in scope, steps, verification, and exit criteria before implementation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", type=slug, help="initiative directory name")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="existing project root (default: cwd)")
    parser.add_argument("--title", help="initiative display title (default: derived from name)")
    parser.add_argument("--phase", action="append", type=slug, help="phase slug; repeat in execution order (default: foundation)")
    parser.add_argument("--schema-version", type=int, choices=(1, 2), default=1, help="plan format version (default: 1; version 2 is opt-in)")
    parser.add_argument("--independent", action="store_true", help="start with no phase dependencies; edit dependsOn for mixed tracks")
    parser.add_argument("--outline", action="append", type=slug, default=[], help="phase slug to scaffold with only objective, scope, and exit criteria")
    args = parser.parse_args()
    if args.schema_version != 2 and (args.independent or args.outline):
        parser.error("--independent and --outline require explicit --schema-version 2")
    if not set(args.outline).issubset(args.phase or ["foundation"]):
        parser.error("--outline must name a configured phase")
    if args.title is not None and (not args.title.strip() or '\n' in args.title or '\r' in args.title):
        parser.error("--title must be a nonblank single line")
    if args.phase and (len(args.phase) > 100 or len(set(args.phase)) != len(args.phase)):
        parser.error("provide at most 100 unique phase slugs")
    try:
        scaffold(args)
    except subprocess.CalledProcessError as error:
        print(error.stderr or error.stdout, file=sys.stderr)
        print("Scaffold validation failed; project files were not written.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
