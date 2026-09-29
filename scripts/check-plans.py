#!/usr/bin/env python3
"""Validate plan manifests and local Markdown contracts; no network access."""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    sys.exit("Missing jsonschema; see phased-planning SKILL.md for isolated setup.")

SKILL_ROOT = Path(__file__).resolve().parents[1]
PHASE_HEADINGS = (
    "Objective", "Scope", "Out of scope", "Prerequisites",
    "Implementation steps", "Verification", "Exit criteria", "Completion evidence",
)
OUTLINE_HEADINGS = ("Objective", "Scope", "Exit criteria")
HANDOFF_HEADINGS = (
    "What is built", "Verification evidence", "Blockers and decisions",
    "Next session", "Shelving reason",
)
SLICE_PHASE_HEADINGS = tuple("Planned slices" if h == "Implementation steps" else h for h in PHASE_HEADINGS)
PHASE_ID_RE = re.compile(r"^(\d{2})([a-z]*)$")


def phase_sort_key(phase_id):
    match = PHASE_ID_RE.match(phase_id)
    if not match:
        return (999, phase_id)
    return (int(match.group(1)), match.group(2))


def validate_phase_order(phases, errors):
    """Manifest order must match ascending phase sort keys (supports 06, 06b, 06c, 07)."""
    keys = [phase_sort_key(p["id"]) for p in phases]
    if keys != sorted(keys):
        errors.append("phases: IDs must be listed in ascending order (base NN, then insertions e.g. 06b, then next base)")
    for index in range(1, len(keys)):
        if keys[index] <= keys[index - 1]:
            errors.append(f"phase {phases[index]['id']}: duplicate or out-of-order phase ID")


def check_document(directory, name, headings, errors):
    path = directory / name
    if path.is_symlink() or not path.is_file():
        errors.append(f"{name}: must be an existing regular local file")
        return
    content = path.read_text(encoding="utf-8")
    # Ignore headings inside fenced examples.
    content = re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*$", "", content)
    sections = re.split(r"(?m)^## (.+?)\s*$", content)
    bodies = dict(zip(sections[1::2], sections[2::2]))
    for heading in headings:
        if not bodies.get(heading, "").strip():
            errors.append(f"{name}: missing or empty '## {heading}' section")
    if not content.strip():
        errors.append(f"{name}: document is empty")


def check_epic_slice(root, phase, errors):
    """A slice-executed phase points at a real epic slice whose state matches the phase."""
    phase_id, status, ref = phase["id"], phase["status"], phase.get("epicSlice")
    if not ref:
        if status != "pending":
            errors.append(f"phase {phase_id}: execution mode slices requires epicSlice once the phase is {status}")
        return
    path = (root / ref)
    if ".." in Path(ref).parts or path.is_symlink() or not path.is_file():
        errors.append(f"phase {phase_id}: epicSlice {ref} must be an existing regular file under the repository")
        return
    try:
        slice_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        errors.append(f"phase {phase_id}: epicSlice {ref} is not readable JSON: {error}")
        return
    if slice_data.get("sliceType") != "epic-slice":
        errors.append(f"phase {phase_id}: epicSlice {ref} must have sliceType epic-slice")
    slice_status = slice_data.get("status")
    if status == "complete" and slice_status != "done":
        errors.append(f"phase {phase_id}: complete phase requires its epic slice to be done (close it with the slice system, not by hand); it is {slice_status}")
    if status in ("active", "blocked") and slice_status in ("done", "cancelled"):
        errors.append(f"phase {phase_id}: epic slice is {slice_status}; complete or re-plan the phase")


def validate(directory, validator, root=None):
    errors = []
    root = Path(root) if root else directory.parent.parent
    manifest = directory / "plan.json"
    if manifest.is_symlink():
        return ["plan.json must not be a symlink"]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for error in validator.iter_errors(data):
        location = ".".join(map(str, error.absolute_path)) or "$"
        errors.append(f"plan.json:{location}: {error.message}")
    if errors:
        return errors

    if directory.name != "_template" and data["id"] != directory.name:
        errors.append("plan.json:id must match the initiative directory name")
    check_document(directory, "README.md", ("Phase index", "Architectural references"), errors)
    check_document(directory, "PLAN-STATUS.md", HANDOFF_HEADINGS, errors)
    phases = data["phases"]
    plan_mode = data.get("execution", {}).get("mode", "phase-doc")
    validate_phase_order(phases, errors)
    version = data["schemaVersion"]
    previous = {}
    running = []
    documents = set()
    for index, phase in enumerate(phases):
        phase_id = phase["id"]
        if not PHASE_ID_RE.match(phase_id):
            errors.append(f"phase {phase_id}: ID must be NN or NNx (e.g. 06, 06b)")
        document = phase["document"]
        if not document.startswith(f"PHASE-{phase_id}-"):
            errors.append(f"phase {phase_id}: document filename must match phase ID")
        if document in documents:
            errors.append(f"phase {phase_id}: duplicate document")
        documents.add(document)
        slice_mode = phase.get("execution", plan_mode) == "slices"
        phase_headings = SLICE_PHASE_HEADINGS if slice_mode else PHASE_HEADINGS
        check_document(directory, document,
                       OUTLINE_HEADINGS if phase.get("type") == "outline" else phase_headings, errors)
        if slice_mode:
            check_epic_slice(root, phase, errors)
        elif phase.get("epicSlice"):
            errors.append(f"phase {phase_id}: epicSlice requires slice execution (plan execution.mode or the phase's execution)")
        if version == 1 and phase.get("type") == "outline":
            errors.append(f"phase {phase_id}: outlines require schemaVersion 2")
        for dependency in phase["dependsOn"]:
            if dependency not in previous:
                errors.append(f"phase {phase_id}: dependency {dependency} must be an earlier phase")
            elif phase_sort_key(dependency) >= phase_sort_key(phase_id):
                errors.append(f"phase {phase_id}: dependency {dependency} must sort before this phase")
        prerequisites = previous if version == 1 else {
            dependency: previous.get(dependency) for dependency in phase["dependsOn"]
        }
        if phase["status"] != "pending" and any(
            state != "complete" for state in prerequisites.values()
        ):
            errors.append(f"phase {phase_id}: required dependencies must be complete before starting")
        if phase["status"] in ("active", "blocked"):
            running.append(phase)
        previous[phase_id] = phase["status"]

    epics = [p["epicSlice"] for p in phases if p.get("epicSlice")]
    if len(epics) != len(set(epics)):
        errors.append("epicSlice paths must be unique per phase")

    for orphan in directory.glob("PHASE-*.md"):
        if orphan.name not in documents:
            errors.append(f"{orphan.name}: phase document is absent from plan.json")

    readme = directory / "README.md"
    if readme.is_file() and not readme.is_symlink():
        links = re.findall(r"\[[^\]]+\]\((PHASE-[^)]+\.md)\)", readme.read_text(encoding="utf-8"))
        if links != [phase["document"] for phase in phases]:
            errors.append("README.md: link each phase once, in manifest order")

    status = data["status"]
    if version == 1:
        if status in ("active", "blocked"):
            if len(running) != 1 or running[0]["id"] != data["activePhase"]:
                errors.append("active/blocked initiative must point to exactly one active/blocked phase")
            elif running[0]["status"] != status:
                errors.append("initiative status must match its current phase status")
        elif running or data["activePhase"] is not None:
            errors.append("draft/complete/shelved initiatives require activePhase null and no running phase")
    else:
        running_ids = {phase["id"] for phase in running}
        if set(data["activePhases"]) != running_ids:
            errors.append("activePhases must list exactly the active/blocked phase IDs")
        if status == "active" and not any(p["status"] == "active" for p in running):
            errors.append("active initiative requires at least one active phase")
        if status == "blocked" and (not running or any(p["status"] != "blocked" for p in running)):
            errors.append("blocked initiative requires running phases to be blocked with none active")
        if status in ("draft", "complete", "shelved") and running:
            errors.append("draft/complete/shelved initiatives require no running phases")
    if status == "draft" and any(p["status"] != "pending" for p in phases):
        errors.append("draft initiatives require all phases pending")
    if status == "complete" and any(p["status"] != "complete" for p in phases):
        errors.append("complete initiatives require all phases complete")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="*", type=Path, help="initiative directories; default: all plus template")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    args = parser.parse_args()
    root = args.root.resolve()
    schema_path = root / "PLANS/plan.schema.json"
    if not schema_path.is_file():
        schema_path = SKILL_ROOT / "assets/plan.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    directories = [path if path.is_absolute() else root / path for path in args.directories]
    if not directories:
        plans = root / "PLANS"
        if not plans.is_dir():
            parser.error(f"No PLANS directory under {root}; supply plan directories explicitly")
        directories = sorted(path for path in plans.iterdir() if path.is_dir())
    if not directories:
        parser.error("No plan directories found")
    failed = False
    for directory in directories:
        try:
            if directory.is_symlink():
                errors = ["initiative directory must not be a symlink"]
            else:
                errors = validate(directory, validator, root)
        except (OSError, ValueError) as error:
            errors = [str(error)]
        for error in errors:
            print(f"ERROR {directory}: {error}", file=sys.stderr)
        failed |= bool(errors)
    if failed:
        return 1
    print(f"Structurally validated {len(directories)} plan directory/directories (including template when selected).")
    print("Content quality, evidence truth, and exit-criterion satisfaction require human or agent review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
