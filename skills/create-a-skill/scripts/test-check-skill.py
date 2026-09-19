#!/usr/bin/env python3
"""Regression tests for check-skill.py.

Every test here exists because the rule it covers was once wrong. The first
version of the checker had seven defects; four of them made it report success on
a skill that was broken, which is the worst failure mode a checker has. A rule
without a test is a rule that will quietly rot back.

Standard library only, no test framework, so it runs anywhere Python does.

    python test-check-skill.py
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Importing the checker would otherwise leave a __pycache__ beside it, and a
# skill that ships a rule against compiled files should not create one by being
# tested. The checker warns about them, correctly, so the suite must not make
# them.
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("check_skill", HERE / "check-skill.py")
check_skill = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check_skill)

PASSED: list[str] = []
FAILED: list[str] = []


def frontmatter(name: str, description: str = "Does a thing. Use when testing the checker.") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n"


def fixture(root: Path, folder: str, body: str, name: str | None = None, extra: dict[str, str] | None = None) -> Path:
    path = root / folder
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(frontmatter(name or folder) + body, encoding="utf-8")
    for filename, content in (extra or {}).items():
        (path / filename).write_text(content, encoding="utf-8")
    return path


def expect(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  ok    {label}")
    else:
        FAILED.append(label)
        print(f"  FAIL  {label}{(' — ' + detail) if detail else ''}")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)

        print("human-facing files")
        # The headline anti-pattern. The first pattern was anchored to a bare
        # word, so `README.md` never matched `^readme$`.
        path = fixture(root, "human-files", "", extra={
            "README.md": "# readme\n",
            "CHANGELOG.md": "# changelog\n",
            "INSTALLATION_GUIDE.md": "# install\n",
            "notes.md": "# notes\n",
        })
        failures = " ".join(check_skill.check(path).failures)
        for filename in ("README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "notes.md"):
            expect(f"{filename} is reported", filename in failures, failures[:90] or "nothing reported")

        print("absolute paths")
        check_skill.check(root / "human-files")
        path = fixture(root, "bare-path", "\nDo not read from /home/ci/cache, it is stale.\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("an unquoted absolute path is reported even on a line saying 'not'", "/home/" in failures, failures[:90] or "hidden")

        path = fixture(root, "quoted-example", "\nNever write `C:\\Users\\me\\file.txt` in a skill.\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("a quoted counter-example is still skipped", "absolute path" not in failures, failures[:90])

        path = fixture(root, "eg-path", "\nCopy the output to e.g. C:\\Users\\me\\report.xlsx first.\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("a bare path after 'e.g.' is reported, not silently swallowed", "absolute path" in failures, "not reported")

        print("flat single-file skills")
        flat_root = root / "flatroot"
        flat_root.mkdir(parents=True, exist_ok=True)
        (flat_root / "quick-note.md").write_text(frontmatter("quick-note"), encoding="utf-8")
        result = check_skill.check(flat_root)
        expect("a matching flat skill passes", not result.failures, " ".join(result.failures)[:90])

        (flat_root / "other-note.md").write_text(frontmatter("other-note"), encoding="utf-8")
        (flat_root / "quick-note.md").write_text(frontmatter("wrong-name"), encoding="utf-8")
        (flat_root / "other-note.md").unlink()
        result = check_skill.check(flat_root)
        expect("a mismatched flat skill fails against the file name",
               any("file name" in f for f in result.failures), " ".join(result.failures)[:90])

        print("byte-order mark")
        bom_dir = root / "bom"
        bom_dir.mkdir(parents=True, exist_ok=True)
        (bom_dir / "SKILL.md").write_bytes(b"\xef\xbb\xbf" + frontmatter("bom").encode("utf-8"))
        result = check_skill.check(bom_dir)
        expect("a BOM does not break frontmatter parsing",
               not any("no YAML frontmatter" in f for f in result.failures), " ".join(result.failures)[:90])
        expect("a BOM is reported as a byte-order mark",
               any("byte-order mark" in w for w in result.warnings), " ".join(result.warnings)[:90])

        print("recursive search")
        deep = root / "project" / ".agents" / "skills" / "hidden-skill"
        deep.mkdir(parents=True, exist_ok=True)
        (deep / "SKILL.md").write_text(frontmatter("hidden-skill"), encoding="utf-8")
        found = check_skill.collect_targets(root / "project")
        expect("a skill inside a dot-directory is found", len(found) == 1 and found[0] == deep,
               f"found {len(found)}: {[str(p) for p in found][:3]}")

        # The first recursive implementation descended into a skill's own
        # references/ folder, saw one .md file, and reported it as a flat skill
        # with no frontmatter: a repair that invented a defect.
        (deep / "references").mkdir(exist_ok=True)
        (deep / "references" / "install-methods.md").write_text("# a document, not a skill\n", encoding="utf-8")
        found = check_skill.collect_targets(root / "project")
        expect("a single document inside references/ is not mistaken for a flat skill",
               len(found) == 1, f"found {len(found)}: {[p.name for p in found]}")

        flat_root2 = root / "flatroot2"
        flat_root2.mkdir(parents=True, exist_ok=True)
        (flat_root2 / "solo.md").write_text(frontmatter("solo"), encoding="utf-8")
        nested = flat_root2 / "nested"
        nested.mkdir()
        (nested / "solo.md").write_text(frontmatter("solo"), encoding="utf-8")
        expect("a flat skill passed explicitly is still found",
               check_skill.locate_skill_file(nested)[0] is not None, "not located")
        expect("a flat skill is not claimed during a recursive walk",
               check_skill.locate_skill_file(nested, allow_flat=False)[0] is None, "claimed")

        # Turning flat detection off during the walk fixed one false positive and
        # created a real one: a root holding nothing but flat skills reported
        # "no skill found".
        flat_only = root / "flat-only"
        flat_only.mkdir(parents=True, exist_ok=True)
        (flat_only / "quick-note.md").write_text(frontmatter("quick-note"), encoding="utf-8")
        found = check_skill.collect_targets(flat_only)
        expect("a root holding only a flat skill is found by the walk",
               len(found) == 1 and found[0] == flat_only, f"found {len(found)}")

        print("files that are not human-facing")
        path = fixture(root, "scripts-at-root", "", extra={"install.sh": "#!/bin/sh\necho hi\n"})
        failures = " ".join(check_skill.check(path).failures)
        expect("a script called install.sh is not mistaken for a human document",
               "install.sh" not in failures, failures[:90])

        path = fixture(root, "readme-in-references", "\nSee references for detail.\n")
        (path / "references").mkdir(exist_ok=True)
        (path / "references" / "README.md").write_text("# readme\n", encoding="utf-8")
        failures = " ".join(check_skill.check(path).failures)
        expect("a README inside references/ is reported too",
               "references/README.md" in failures, failures[:90] or "not reported")

        print("folded descriptions")
        folded = root / "folded"
        folded.mkdir(parents=True, exist_ok=True)
        (folded / "SKILL.md").write_text(
            "---\nname: folded\ndescription: >\n  Handles documents of many kinds.\n  Nothing here says when to reach for it.\n---\n\nBody.\n",
            encoding="utf-8")
        warnings = " ".join(check_skill.check(folded).warnings)
        expect("a folded description is parsed and judged",
               "does not say when to use" in warnings, warnings[:90] or "not judged")

        print("the same rules inside references/")
        # The first version read SKILL.md and stopped, so every content rule was
        # unenforced in the one folder the document tells authors to use.
        path = fixture(root, "refs-dated", "\nSee [the notes](references/notes.md).\n")
        (path / "references").mkdir(exist_ok=True)
        (path / "references" / "notes.md").write_text(
            "# Notes\n\nAs of Q4 2024 the API took two arguments.\n", encoding="utf-8")
        warnings = " ".join(check_skill.check(path).warnings)
        expect("a dated fact inside references/ is reported",
               "will age badly" in warnings and "references/notes.md" in warnings, warnings[:100] or "not reported")

        path = fixture(root, "refs-absolute", "\nSee [the notes](references/notes.md).\n")
        (path / "references").mkdir(exist_ok=True)
        (path / "references" / "notes.md").write_text("# Notes\n\nRead /home/ci/cache first.\n", encoding="utf-8")
        failures = " ".join(check_skill.check(path).failures)
        expect("an absolute path inside references/ is reported", "/home/" in failures, failures[:100] or "not reported")

        path = fixture(root, "refs-broken-link", "\nSee [the notes](references/notes.md).\n")
        (path / "references").mkdir(exist_ok=True)
        (path / "references" / "notes.md").write_text("# Notes\n\nSee [detail](detail.md).\n", encoding="utf-8")
        failures = " ".join(check_skill.check(path).failures)
        expect("a broken link inside references/ is reported", "detail.md" in failures, failures[:100] or "not reported")

        print("compiled files")
        # The author of this checker committed a .pyc while shipping a rule
        # against binary files, and the skip list hid it from the checker itself.
        path = fixture(root, "has-bytecode", "")
        (path / "scripts").mkdir(exist_ok=True)
        (path / "scripts" / "__pycache__").mkdir(exist_ok=True)
        (path / "scripts" / "__pycache__" / "thing.cpython-312.pyc").write_bytes(b"\x00\x01\x02")
        warnings = " ".join(check_skill.check(path).warnings)
        expect("a compiled file is reported even inside __pycache__",
               "compiled or binary" in warnings, warnings[:100] or "not reported")

        print("the size ceiling")
        path = fixture(root, "long-body", "\n" + "\n".join(f"line {i}" for i in range(520)) + "\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("a body over 500 lines fails", "500" in failures, failures[:100] or "not reported")

        path = fixture(root, "padded-body", "\n" + "\n".join([""] * 520) + "\nshort\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("padding with blank lines does not hide a long body", "500" in failures, failures[:100] or "passed on blank lines")

        print("word boundaries")
        # Both of these were real false positives found by running the checker
        # over other people's skills.
        path = fixture(root, "uri-not-a-drive", "\nconst m = uri.match(/^file:\\/\\/documents\\/(.+)$/);\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("e:\\ inside file:\\/\\/ is not read as a Windows drive",
               "absolute path" not in failures, failures[:90])

        path = fixture(root, "prose-not-a-path", "\n- Better scripts/tools that produced better output?\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("an unquoted prose mention of scripts/tools is not a broken link",
               "does not exist" not in failures, failures[:90])

        path = fixture(root, "quoted-missing-script", "\nRun `scripts/missing.py` to begin.\n")
        failures = " ".join(check_skill.check(path).failures)
        expect("a quoted path to a file that is not there is still reported",
               "missing.py" in failures, failures[:90] or "not reported")

        path = fixture(root, "script-without-suffix", "\nRun `scripts/helper` to begin.\n")
        (path / "scripts").mkdir(exist_ok=True)
        (path / "scripts" / "helper.py").write_text("print('ok')\n", encoding="utf-8")
        failures = " ".join(check_skill.check(path).failures)
        expect("a script named without its extension resolves",
               "does not exist" not in failures, failures[:90])

        print("name versus folder")
        path = fixture(root, "folder-name", "", name="different-name")
        failures = " ".join(check_skill.check(path).failures)
        expect("a name/folder mismatch fails", "does not match" in failures, "not reported")
        expect("the mismatch message does not claim the loader ignores the file",
               "ignores the file" not in failures, failures[:90])

        print("a clean skill")
        path = fixture(root, "clean-skill", "\nRun `scripts/helper.py` and read [the reference](references/notes.md).\n")
        (path / "scripts").mkdir(exist_ok=True)
        (path / "scripts" / "helper.py").write_text("print('ok')\n", encoding="utf-8")
        (path / "references").mkdir(exist_ok=True)
        (path / "references" / "notes.md").write_text("notes\n", encoding="utf-8")
        result = check_skill.check(path)
        expect("a correct skill has no failures", not result.failures, " ".join(result.failures)[:120])

        print("time-sensitive text")
        path = fixture(root, "dated", "\nAs of Q4 2024 the API took two arguments.\n")
        warnings = " ".join(check_skill.check(path).warnings)
        expect("a bare date is reported", "will age badly" in warnings, warnings[:90])

        path = fixture(root, "dated-quoted", "\n`As of Q4 2024` rots within a quarter, so do not write it.\n")
        warnings = " ".join(check_skill.check(path).warnings)
        expect("a quoted counter-example date is skipped", "will age badly" not in warnings, warnings[:90])

    print()
    print(f"{len(PASSED)} passed, {len(FAILED)} failed")
    for label in FAILED:
        print(f"  failed: {label}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
