# Three ways the scanning gate is misread

Moved out of `SKILL.md` when the family's token budget was enforced: the skill was over the 5,000-token body the standard recommends, while passing the 500-line check that used to stand in for it.

### Three ways this gate is misread

Each one found by the same agent, each one real:

**Scope wider than the tool.** The gate says *any file, script, repository or archive*. The
scanner now opens **every** file in a folder — an earlier version filtered the walk to nine text
extensions, missed two `.txt` files, and reported the folder clean with exit 0 — and a file it
cannot read, because it holds a NUL byte in its first block, is **named as unreadable rather
than skipped in silence**. What it still cannot do is **look inside an archive, an image, a PDF
or a notebook.** When the thing is one of those, the tool is not the gate: unpack it, read it by
hand, or say plainly that the gate could not run on it. **"The scanner passed" is false when the
scanner never opened the file** — and "the scanner passed" is also false when it opened the file
and told you it could not read it.

**A threat that arrives by being read.** The scanner guards what is **on disk**. Text fetched
into a session and never saved **never touches a disk**, so the tool never sees it — and that
is precisely the prompt-injection shape this gate exists for. **Save it, then scan it**, or
read it with the gate's rule in hand and say that is what you did.

**A page read in a browser never touches the disk the scanner reads.** The gate says scan
before use, and the tool takes a filesystem path — so a page fetched into a session and read
there **cannot be scanned at all**, and the gate as written is unexecutable on that path. Both
agents routed by this regulation hit it, and one had already read the page before realising.

**The order is download, scan, read.** Save the text to a file, run the scanner on the file,
then read it with the findings in hand. Reading first and scanning afterwards is not the gate;
it is the gate performed after the thing it guards.

**Which tool, and where it is.** The script is **`check-external-skill.py`**, in the `scripts/` directory of the skill
**`find-a-skill`**, in this family's skills root. Three agents were routed by this regulation
and **all three had to find the path in the router's source**, because the prose named the
scan without saying where it lives. A gate a reader cannot run is a gate that gets skipped.

**The tool is itself third-party.** The scanner's hidden-character rules are adopted from
NVIDIA/SkillSpector, Apache 2.0, named in its own source. That is outside content inside the
instrument the gate declares required, and self-scanning is not a gate. **Say where the tool
came from and what it does not cover**; do not treat its silence as coverage.
