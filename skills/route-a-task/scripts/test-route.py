#!/usr/bin/env python3
"""Test the regulation's own triggers, because nothing else does.

SKILL.md says of itself: "the strengths have not been tested. No task has been routed by
this table and then checked against what actually happened." That is true of the strengths
and was never true of the triggers - they were tested by accident, by three agents, and
every one of the four defects they found was a trigger defect:

  * G3 fired on "a car won't start" and demanded a Windows hardware collector for a car,
    while "a car will not start" fired nothing. Coverage was keyword-shaped and a
    contraction decided it.
  * G5 existed in the prose for a day with no entry in the router, so it never fired.
  * The sentence that asks for a check - "verify the result independently" - matched
    nothing at all, on a task whose whole difficulty was that the answer could be wrong.
  * "Nothing fired" rendered as a pass. That one is not a trigger defect but it is the
    same class: the empty case was never executed by its author.

So this file is the counter-example library the skill says it lacks, and every case here
is a task an agent actually ran or a phrase this family actually uses. Two directions are
checked, and the second matters more: a gate that does not fire when it should costs a
redo, and a gate that fires when it should not costs the table its credibility.

    python test-route.py
    python test-route.py --list

Exit 0 when every case holds, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Loading route.py by path would leave a __pycache__ directory inside the skill, and the
# checker is right to refuse a compiled file it cannot review - it is the same SC8 shape the
# external-content scanner reports. A test that dirties the thing it tests is a defect, so
# bytecode writing is off before the import below.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent

# The route.py under test is the one next to this file, loaded by path - so the test tests
# the copy it ships with and not whichever one happens to be on sys.path.
spec = importlib.util.spec_from_file_location("route_under_test", HERE / "route.py")
route_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route_module)


# (task, gates that MUST fire, gates that MUST NOT fire, why this case exists)
#
# The third field is the one that found every defect so far, so it is required rather than
# optional: a case with no counter-example is a case nobody thought about.
CASES: list[tuple[str, list[str], list[str], str]] = [
    # --- the task the regulation did not cover, verbatim from the A/B record -----------
    ("compute natural logarithms accurately for arguments near 1, and verify independently",
     ["G6"], ["G1", "G3"],
     "the logarithm agent's task. Matched nothing, and --verify passed the empty record."),
    ("проверить результат независимо",
     ["G6"], [],
     "the same request in Russian, which is the sentence that used to match nothing."),
    ("how many U+200E are in the file",
     ["G6"], [],
     "the epigraphy agent's real question, and a count is the archetypal quietly-wrong value."),
    ("посчитай среднее по выборке",
     ["G6"], [],
     "the Russian numeric deliverable, to prove the trigger table is not English-only."),
    ("prove that the sum converges",
     ["G6"], [],
     "a proof is a deliverable with no domain in its wording."),

    # --- the false trigger, in both spellings -----------------------------------------
    ("a car won't start",
     [], ["G1", "G2", "G3", "G4", "G5", "G6"],
     "the car agent's task. G3 fired on this and demanded a Windows collector."),
    ("a car will not start",
     [], ["G3"],
     "the same fault spelled out, which fired nothing. A contraction decided a gate."),

    # --- the traps a new gate is most likely to fall into -----------------------------
    ("measure a window so clicks land",
     [], ["G6"],
     "learn-an-interface's own work. A gate keyed on 'measure' fires here and is wrong."),
    ("convert this docx to a pdf",
     [], ["G6"],
     "a conversion, and not a value. A gate keyed on bare 'convert' fires here."),
    ("extract the archive and scan it",
     [], ["G6"],
     "a gate keyed on 'extract the' fires here. G1 must fire, on 'archive'."),
    ("proofread the release notes for typos",
     [], ["G6"],
     "a gate keyed on bare 'proof' fires here, on a spelling task."),
    ("derive the requirements from the interview",
     [], ["G6"],
     "a gate keyed on bare 'derive' fires here, on elicitation."),

    # --- the gates that already worked, so a change to the table is visible -----------
    ("download a skill from github and install it",
     ["G1"], ["G3", "G6"],
     "the first agent ever routed. G1 is the gate this whole family exists for."),
    ("write a new skill for kubernetes",
     ["G2"], ["G1", "G3", "G6"],
     "G2 exists because learn-an-interface was written before anyone searched."),
    ("the laptop reboots and shows a blue screen",
     ["G3"], ["G1", "G6"],
     "G3, on a symptom that is actually a Windows symptom."),
    ("publish the skill and adopt it",
     ["G4"], ["G1", "G2", "G3", "G6"],
     "G4, and this is the gate that has never yet found nothing."),
    ("choose a json library for the parser",
     ["G5"], ["G1", "G3", "G6"],
     "G5, which existed in prose with no router entry for a day and never fired."),
    ("which tool should i use to read a csv",
     ["G5"], ["G6"],
     "G5's second spelling, because one phrasing of a gate is a gate with a hole in it."),

    # --- matching by letters instead of by words --------------------------------------
    # These six are not hypothetical. Each one fired the named gate on the previous
    # version, and each is a gate telling an agent to stop and do something unrelated.
    ("summarise the report from last week",
     [], ["G1"],
     "'report' contains 'repo', so G1 ordered a malware scan for a summary."),
    ("relationship between the two settings",
     [], ["G4"],
     "'relationship' contains 'ship', so G4 demanded an independent reader."),
    ("the shipment arrived on time",
     [], ["G4"],
     "and 'shipment' contains it too."),
    ("improve the skill description",
     [], ["G6"],
     "'improve' contains 'prove'. A gate keyed on bare 'prove' fires on every improvement."),
    ("the operations manual needs a rewrite",
     [], ["G6"],
     "'operations' contains 'ratio'. So do 'exploration' and 'configuration'."),
]


# (task, tools that MUST be suggested, tools that must NOT be, why)
#
# The routes are checked separately because the worst false positive in the file was a
# route and not a gate, and it was invisible: the interface route carried the trigger
# "form" for a dialog, and "form" is inside "from". Every sentence containing "from" was
# told to run the Windows preflight before touching a window.
ROUTE_CASES: list[tuple[str, list[str], list[str], str]] = [
    ("copy the file from disk",
     [], ["manage-windows preflight, then learn-an-interface"],
     "'from' contains 'form' - the worst of them."),
    ("format the document",
     [], ["manage-windows preflight, then learn-an-interface"],
     "'format' contains it."),
    ("read this information before writing",
     [], ["manage-windows preflight, then learn-an-interface"],
     "and 'information'."),
    ("improve the performance of the query",
     [], ["manage-windows preflight, then learn-an-interface"],
     "and 'performance'."),
    ("click the button in the dialog",
     ["manage-windows preflight, then learn-an-interface"], [],
     "the route that must still fire when a window is really being driven."),
    ("design the reward signal for the bandit",
     ["design-a-reward"], [],
     "and the reward route must survive, on the word 'reward'."),
    ("post the weekly digest to our vk community",
     ["manage-vk"], [],
     "the newest tool in the family needs an entry point, or it is the same defect "
     "route-a-task was written to fix."),
    ("опубликовать пост в сообществе вконтакте",
     ["manage-vk"], [],
     "and the Russian phrasing must reach it too, because that is how it will be asked."),
]


def fired(task: str) -> list[str]:
    return [gate["id"] for gate in route_module.route(task)["gates"]]


def check_cases() -> tuple[int, int]:
    passed = failed = 0
    for task, must, must_not, why in CASES:
        got = fired(task)
        trouble: list[str] = []
        for gate in must:
            if gate not in got:
                trouble.append(f"{gate} did not fire")
        for gate in must_not:
            if gate in got:
                trouble.append(f"{gate} fired but must not")
        if trouble:
            failed += 1
            print(f"  FAIL  {task}")
            print(f"        {'; '.join(trouble)}")
            print(f"        fired: {', '.join(got) or 'nothing'}")
            print(f"        why it matters: {why}")
        else:
            passed += 1
            print(f"  ok    {task}")
    return passed, failed


def check_routes() -> tuple[int, int]:
    passed = failed = 0
    for task, must, must_not, why in ROUTE_CASES:
        suggested = [one["tool"] for one in route_module.route(task)["routes"]]
        trouble = [f"{tool} was not suggested" for tool in must if tool not in suggested]
        trouble += [f"{tool} was suggested but must not be" for tool in must_not
                    if tool in suggested]
        if trouble:
            failed += 1
            print(f"  FAIL  {task}")
            print(f"        {'; '.join(trouble)}")
            print(f"        suggested: {', '.join(suggested) or 'nothing'}")
            print(f"        why it matters: {why}")
        else:
            passed += 1
            print(f"  ok    {task}")
    return passed, failed


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / "route.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def check_cli() -> tuple[int, int]:
    passed = failed = 0

    def expect(name: str, condition: bool, detail: str) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ok    {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")
            print(f"        {detail}")

    with tempfile.TemporaryDirectory() as folder:
        empty = Path(folder) / "empty.json"
        empty.write_text(json.dumps({"gates": {}}), encoding="utf-8")
        full = Path(folder) / "full.json"
        full.write_text(json.dumps({"gates": {"G6": True}}), encoding="utf-8")

        # Three different sentences, and the whole design is that they stay different.
        done = run("compute the average", "--verify", str(full))
        expect("a gate with a record exits 0",
               done.returncode == 0 and "Nothing was forgotten" in done.stdout,
               f"exit {done.returncode}\n{done.stdout}")

        missing = run("compute the average", "--verify", str(empty))
        expect("a fired gate with no record exits 1 and reprints the step",
               missing.returncode == 1 and "second route" in missing.stdout,
               f"exit {missing.returncode}\n{missing.stdout}")

        vacuous = run("a car won't start", "--verify", str(empty))
        expect("no gate fired exits 3 and says NOT COVERED is not CLEAR",
               vacuous.returncode == 3 and "NO GATE FIRED" in vacuous.stdout,
               f"exit {vacuous.returncode}\n{vacuous.stdout}")

        unmatched = run("reticulate the splines")
        expect("nothing matched at all exits 2",
               unmatched.returncode == 2,
               f"exit {unmatched.returncode}\n{unmatched.stdout}")

        blank = run("")
        expect("no task at all is an argument error, not a pass",
               blank.returncode != 0,
               f"exit {blank.returncode}")

    rendered = route_module.render(route_module.route("compute the average"))
    expect("a fired gate prints its step, not just a tool name",
           "second route" in rendered,
           rendered)
    expect("a fired gate prints the record it owes",
           "record" in rendered,
           rendered)

    # The defect this test was written to catch, after it had been on screen for a day:
    # "read nothing - this gate is a record, not a tool for why, not only what".
    for gate in route_module.GATES:
        if gate["tool"].startswith("nothing"):
            line = [one for one in route_module.render(
                route_module.route(" ".join(gate["when"][:2]))).splitlines()
                if "method" in one]
            expect(f"[{gate['id']}] a gate with no tool reads as a sentence",
                   line and "read nothing" not in line[0],
                   line[0] if line else "no method line rendered")

    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="print the cases and stop")
    args = parser.parse_args()

    # cp1251 is the console default on a Russian Windows, and this file prints tasks in two
    # alphabets. A crash while printing a finding is a finding thrown away.
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    if args.list:
        for task, must, must_not, why in CASES:
            print(f"  {task}")
            print(f"      must fire: {', '.join(must) or 'nothing'}")
            print(f"      must not:  {', '.join(must_not) or 'nothing'}")
            print(f"      why:       {why}")
        return 0

    print("triggers - both directions")
    passed, failed = check_cases()
    print()
    print("routes - what must not be suggested")
    route_passed, route_failed = check_routes()
    print()
    print("the command line")
    cli_passed, cli_failed = check_cli()

    total_passed = passed + route_passed + cli_passed
    total_failed = failed + route_failed + cli_failed
    print()
    print(f"  {total_passed} ok, {total_failed} failed")
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
