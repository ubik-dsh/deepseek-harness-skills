#!/usr/bin/env python3
"""Build and validate the record of a hearing — the mechanical half of the rules.

This does not judge. It refuses to write down a hearing that breaks the rules the
skill sets out, so that the rules are enforced rather than requested:

  * **a charge with no evidence citation is not a charge.** "Vague unease" has no
    place to go, because `evidence` is required and checked against the artefact's
    own text if the artefact is given.
  * **every charge must be answered.** A defence that ignores a charge is not a
    defence, and the recorder says which one was skipped.
  * **"reject the skill, take these parts" must name the parts.** The verdict that
    this whole skill exists for cannot be recorded empty.

Everything else is formatting, so that two hearings can be compared later without
reading both.

    python hearing.py --new <skill-name> > sheet.json
    python hearing.py sheet.json                  # validate and render
    python hearing.py sheet.json --artefact <path-to-SKILL.md>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERDICTS = (
    "acquit",
    "keep with a boundary",
    "fix",
    "reject the skill, take these parts",
    "reject entirely",
)

BLANK = {
    "skill": "",
    "claim": "",
    "worth_keeping": "",
    "worthless": "",
    "falsifiable_by": "",
    "charges": [
        {
            "id": "C1",
            "charge": "",
            "level": "premise",
            "evidence": "",
            "severity": 5,
        }
    ],
    "defence": [
        {
            "id": "D1",
            "answers": "C1",
            "point": "",
            "evidence": "",
        }
    ],
    "must_not_destroy": "",
    "rating": {"prosecutor": 5, "defence": 5, "decided_by": ""},
    "verdict": "fix",
    "order": [],
    "boundary": "",
}


def load_sheet(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"  no sheet at {path}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as trouble:
        print(f"  {path} is not valid JSON: {trouble}", file=sys.stderr)
        raise SystemExit(2)


def check(sheet: dict, artefact: str | None) -> list[str]:
    """Every rule this recorder enforces, as a list of complaints."""
    problems: list[str] = []

    for field in ("skill", "claim", "worth_keeping", "worthless", "falsifiable_by"):
        if not str(sheet.get(field, "")).strip():
            problems.append(f"the charge sheet is incomplete: '{field}' is empty")

    # A falsification condition must be checkable. These are the shapes that are not.
    theatre = ("if evidence emerges", "if it turns out", "if problems appear",
               "if issues arise", "to be determined", "unclear")
    condition = str(sheet.get("falsifiable_by", "")).lower()
    if condition and any(phrase in condition for phrase in theatre):
        problems.append(
            "the falsification condition is calibration theatre - it names no "
            "observation that could settle the question")

    charges = sheet.get("charges", [])
    if not isinstance(charges, list) or len(charges) == 0:
        if sheet.get("verdict") != "acquit":
            problems.append(
                "no charges were filed, so the verdict cannot be anything but 'acquit'")

    text = None
    if artefact is not None:
        try:
            text = Path(artefact).read_text(encoding="utf-8", errors="replace")
        except OSError as trouble:
            problems.append(f"the artefact could not be read: {trouble}")

    charge_ids = set()
    for index, charge in enumerate(charges, 1):
        where = f"charge {charge.get('id', index)}"
        cid = str(charge.get("id", "")).strip()
        if not cid:
            problems.append(f"{where}: no id")
        elif cid in charge_ids:
            problems.append(f"{where}: the id is used twice")
        charge_ids.add(cid)

        if not str(charge.get("charge", "")).strip():
            problems.append(f"{where}: states nothing")

        evidence = str(charge.get("evidence", "")).strip()
        if not evidence:
            problems.append(
                f"{where}: cites no evidence - a vague unease is not a charge")
        elif text is not None and evidence not in text:
            problems.append(
                f"{where}: the cited evidence does not appear in the artefact - "
                f"{evidence[:60]!r}")

        level = str(charge.get("level", "")).strip().lower()
        if level not in ("premise", "execution"):
            problems.append(
                f"{where}: level must be 'premise' or 'execution', not {level!r} - "
                "they lead to different verdicts")

        severity = charge.get("severity")
        if not isinstance(severity, int) or not 1 <= severity <= 10:
            problems.append(f"{where}: severity must be a whole number from 1 to 10")
        if str(charge.get("charge", "")).strip() and len(
                str(charge.get("charge", "")).strip()) < 25:
            problems.append(f"{where}: too short to be a concrete harm")

    defence = sheet.get("defence", [])
    if charge_ids and not defence:
        problems.append("no defence was filed against a filed charge")

    answered = set()
    for index, point in enumerate(defence, 1):
        where = f"defence {point.get('id', index)}"
        if not str(point.get("point", "")).strip():
            problems.append(f"{where}: states nothing")
        if not str(point.get("evidence", "")).strip():
            problems.append(f"{where}: argues from no evidence")
        answers = point.get("answers")
        if isinstance(answers, list):
            targets = answers
        elif answers:
            targets = [answers]
        else:
            targets = []
        if not targets:
            problems.append(f"{where}: answers no charge")
        for target in targets:
            if str(target) not in charge_ids:
                problems.append(f"{where}: answers {target!r}, which is not a charge")
            else:
                answered.add(str(target))

    for cid in sorted(charge_ids - answered):
        problems.append(f"charge {cid} was never answered by the defence")

    if not str(sheet.get("must_not_destroy", "")).strip():
        problems.append(
            "the defence did not name what any outcome must not destroy - even a "
            "losing defence owes the judge that sentence")

    rating = sheet.get("rating", {})
    for side in ("prosecutor", "defence"):
        value = rating.get(side)
        if not isinstance(value, int) or not 0 <= value <= 10:
            problems.append(f"the {side} rating must be a whole number from 0 to 10")
    if not str(rating.get("decided_by", "")).strip():
        problems.append(
            "the rating does not say what decided it - a score with no sentence "
            "is not a judgement")

    verdict = str(sheet.get("verdict", "")).strip().lower()
    if verdict not in VERDICTS:
        problems.append(f"verdict must be one of: {', '.join(VERDICTS)}")

    if verdict == "reject the skill, take these parts":
        order = sheet.get("order", [])
        if not isinstance(order, list) or len(order) == 0:
            problems.append(
                "the verdict salvages parts and names none - this is the verdict the "
                "whole hearing exists for and it cannot be recorded empty")
        else:
            for index, part in enumerate(order, 1):
                if not str(part.get("part", "")).strip():
                    problems.append(f"order {index}: names no part")
                if not str(part.get("trial", "")).strip():
                    problems.append(
                        f"order {index}: names no trial - a salvaged part kept "
                        "without a trial is a part kept on faith")

    if verdict == "keep with a boundary" and not str(sheet.get("boundary", "")).strip():
        problems.append("the verdict keeps it 'with a boundary' and names none")

    return problems


def render(sheet: dict) -> str:
    lines = [f"# Hearing: {sheet['skill']}", ""]
    lines += [
        "## The charge sheet", "",
        f"**Claim** — {sheet['claim']}", "",
        f"**Worth keeping if** — {sheet['worth_keeping']}", "",
        f"**Worthless if** — {sheet['worthless']}", "",
        f"**Falsifiable by** — {sheet['falsifiable_by']}", "",
        "## The prosecution", "",
    ]
    for charge in sheet.get("charges", []):
        lines += [
            f"**{charge['id']}** ({charge['level']}-level, severity {charge['severity']}/10)",
            "",
            f"> {charge['charge']}",
            "",
            f"Evidence — `{charge['evidence']}`", "",
        ]
    lines += ["## The defence", ""]
    for point in sheet.get("defence", []):
        targets = point.get("answers")
        targets = ", ".join(targets) if isinstance(targets, list) else str(targets)
        lines += [
            f"**{point['id']}** answers {targets}",
            "",
            f"> {point['point']}",
            "",
            f"Evidence — `{point['evidence']}`", "",
        ]
    lines += [
        f"**Must not be destroyed** — {sheet['must_not_destroy']}", "",
        "## The rating", "",
        f"| | |", "|---|---|",
        f"| prosecutor | **{sheet['rating']['prosecutor']}/10** |",
        f"| defence | **{sheet['rating']['defence']}/10** |",
        "", f"Decided by — {sheet['rating']['decided_by']}", "",
        "## The verdict", "",
        f"**{sheet['verdict']}**", "",
    ]
    if sheet.get("boundary"):
        lines += [f"Boundary — {sheet['boundary']}", ""]
    if sheet.get("order"):
        lines += ["### The order", ""]
        for part in sheet["order"]:
            lines += [f"- **{part['part']}**", f"  - trial: {part['trial']}"]
        lines += [""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheet", nargs="?", type=Path)
    parser.add_argument("--new", metavar="SKILL-NAME",
                        help="print a blank sheet and exit")
    parser.add_argument("--artefact", type=Path,
                        help="check each cited piece of evidence against this file")
    parser.add_argument("--json", action="store_true",
                        help="emit the rendered record as JSON instead of markdown")
    args = parser.parse_args()

    if args.new:
        blank = json.loads(json.dumps(BLANK))
        blank["skill"] = args.new
        print(json.dumps(blank, indent=2, ensure_ascii=False))
        return 0

    if args.sheet is None:
        parser.error("give a sheet, or --new <skill-name>")

    sheet = load_sheet(args.sheet)
    problems = check(sheet, str(args.artefact) if args.artefact else None)

    if problems:
        print(f"  the record cannot be written: {len(problems)} problem(s)", file=sys.stderr)
        for problem in problems:
            print(f"    - {problem}", file=sys.stderr)
        return 1

    charges = len(sheet.get("charges", []))
    print(render(sheet) if not args.json else json.dumps(sheet, indent=2, ensure_ascii=False))
    print("", file=sys.stderr)
    print(f"  valid: {charges} charge(s), verdict '{sheet['verdict']}', "
          f"prosecutor {sheet['rating']['prosecutor']}/10 "
          f"against defence {sheet['rating']['defence']}/10", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
