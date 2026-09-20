---
name: check-hardware
description: Read what a Windows machine's hardware actually reports, and tell a healthy component from an unreadable one. Covers the commands that work and the ones that quietly return nothing, why a disk reporting Healthy may not have been checked at all, how to read memory slots rather than memory size, where WHEA and disk errors are logged, what the battery report's two capacities mean, and the order that keeps a diagnosis read-only until there is evidence. Ships a collector that gathers the readings and marks every one it could not take. Use when the user asks what is in their PC, whether a drive or a stick of memory is failing, why a machine reboots or throttles, how hot something runs, how old a battery is, or when a machine behaves badly and the cause is not in the software.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text. scripts/collect.py needs Python 3.8+ on Windows and reads through PowerShell; it takes no reading that changes anything.
metadata:
  spec: https://agentskills.io/specification
  version: 0.1.0
  status: first formulation, assembled from a survey of 132 repositories and one collection of 78
  borrowed_from: Swietlik3d/windows-pc-skills for the frame - symptom to evidence to hypothesis to test, read-only first, and an escalation ladder - which is the best structure found in that survey and is used here; the commands and the traps are ours, and references/readings.md names which is which
  sibling: manage-windows holds the platform - encoding, invocation, where scripts go, and the rule about proving a target before touching it. This skill holds what to read and how not to be fooled by it
---

# Reading a machine

One rule carries this whole skill:

> **A missing reading is not a good reading.**

A disk that reports `Healthy` may be a disk that reports nothing at all — `Get-PhysicalDisk` has
a health field, and a controller that does not answer leaves it at its default rather than
raising an error. A temperature query returns nothing on most machines because the firmware does
not expose one, and "no temperature" reads like "temperature fine" to anyone skimming. **Every
tool in this area fails by returning nothing, and nothing looks like good news.**

So the collector in this skill reports what it read **and what it could not**, and the second
list is the one to look at.

---

## Step 0 — read before you touch

Diagnosis is read-only. The first pass takes every measurement it can and changes nothing: no
driver updates, no `chkdsk /f`, no firmware flash, no BIOS setting toggle. Those come after a
hypothesis, and a hypothesis needs evidence.

The reason is not caution in general. It is that **the cheap repair destroys the evidence for
the expensive fault**: running a repair on a failing drive overwrites the sectors that would
have shown why, and reflashing firmware erases what the old version was doing.

**And a machine with an unclear fault should be left running until it is read**, not rebooted.
A reboot clears the event log entries and the memory state that the fault was in.

## Step 1 — take the readings

```bash
python scripts/collect.py                # everything readable, as JSON
python scripts/collect.py --json out.json
python scripts/collect.py --only disk,memory
```

It gathers: the machine and its firmware, the processor, memory **sizes and slots**, every
physical disk with its bus type and health field, SMART attributes where the drive exposes
them, volumes and free space, the battery's two capacities, thermal zones, GPU adapters and
driver versions, and the hardware errors in the event log.

`references/readings.md` holds the individual commands and what each one can and cannot tell
you. Read it before trusting a single number, because most of them have a limit that is not
obvious from the value.

## Step 2 — separate what is wrong from what is unreadable

For every reading, one of three things is true, and the report must say which:

| | |
|---|---|
| **a value** | the machine answered |
| **empty** | the machine was asked and did not answer — **this is not health** |
| **unavailable** | the tool is not installed, or the rights are insufficient |

The second and third are the interesting ones. A diagnosis that treats all three as "fine"
is not a diagnosis; it is a form filled in.

## Step 3 — symptom, evidence, hypothesis, test

The frame worth taking from the collection that was surveyed:

```
symptom      what the person reports, in their words
evidence     what was read that bears on it, cited
hypothesis   the one thing that would explain both
test         the cheapest observation that would separate it from the alternatives
```

**The hypothesis must be falsifiable by a test you can name.** "The disk is failing" is not a
hypothesis until it is "the disk is failing, which the SMART reallocated-sector count would
show, and a read of the attribute settles it".

And the order matters: **evidence before hypothesis**, because a hypothesis formed first
selects the evidence that agrees with it. That is the same failure as an author testing their
own skill.

## Step 4 — the escalation ladder

When the evidence points at a repair, go up one rung at a time and stop when the symptom goes:

1. **read** — no change;
2. **ask** — a question to the person, or a vendor tool that reports more;
3. **configure** — a setting that is reversible, with the previous value written down;
4. **update** — a driver or firmware, with the version it is replacing written down;
5. **repair** — a filesystem check, a reseat, a partition fix;
6. **replace**.

**Rungs four and five destroy evidence and can lose data.** Name what will be lost before
taking them, and get the person's agreement in their own words. A machine being diagnosed for a
failing disk should not have its firmware updated as a first move.

## The readings that fool people

Each of these is in `references/readings.md` with the command and the limit. The short form:

- **`Get-PhysicalDisk` health is a field, not a test.** A controller that reports no SMART
  leaves it at its default. Read the attributes with `smartctl` before believing it.
- **`Win32_PhysicalMemory` lists the sticks; `Win32_PhysicalMemoryArray` lists the slots.**
  Reading only the first hides an empty slot and a machine running single-channel. **Free
  slots is `MemoryDevices` minus the number of sticks** — a subtraction the two readings make
  possible and neither one states.
- **`Win32_DiskDrive` and `Get-PhysicalDisk` are different views** and disagree about numbers,
  sizes and identification. Know which one you asked.
- **The battery report has two capacities.** Design capacity and full-charge capacity; their
  ratio is the health, and either alone says nothing.
- **Thermal zones are usually absent.** `MSAcpi_ThermalZoneTemperature` answers on some
  machines and returns a plausible wrong number on others. Absence is the common case and is
  not a finding.
- **`wmic` is deprecated and removed from recent builds.** `Get-CimInstance` is the form that
  works everywhere, and a `wmic` failure looks like a missing component rather than a missing
  command.
- **SMART needs a tool that is not part of Windows.** No `smartctl` means no SMART, which means
  the health field is the only thing you have — and it is the thing not to trust.
- **WHEA errors are in the event log**, and a machine that reboots without a bugcheck often
  wrote one there. `Get-WinEvent` for the provider.
- **A virtual machine answers all of this convincingly and describes the host's abstraction.**
  Check whether the machine is virtual before diagnosing its "hardware".

## What this skill does not cover

- **The platform.** `manage-windows` holds the PowerShell traps, the invocation, encoding,
  where generated scripts go, and the rule about proving a target before touching it. This
  skill assumes all of that and does not repeat it.
- **Repair procedures in detail.** The ladder says the order and what each rung costs. What
  `bcdedit` does to a boot record is another skill's subject, and doing it from here would be
  guessing.
- **Physical work.** Reseating memory, cleaning a cooler, replacing a battery — no command
  reaches any of it. Say so rather than pretending a reading is a repair.
- **Any machine that is not Windows.** The commands are Windows. The three-way split between a
  value, an empty answer and an unavailable tool is not, and it travels.

## Refining this skill

Version 0.1.0. The frame came from a collection of 78 Windows-PC skills that are procedural
prose in Polish with almost no commands; the commands and the traps here are ours and are
verified on one machine, which is not many. Most likely to be wrong:

- **The absent-reading list is short.** Every machine exposes a different subset, and no
  attempt was made to survey across vendors. If a reading is absent here that another machine
  provides, that is the list to extend.
- **The thermal section is the weakest.** The number of machines where a temperature is
  readable at all is unknown, and it may be that recommending a vendor tool outright is better
  than trying the WMI class first.
- **The ladder is untested.** No repair has been carried out under it. It is a reading of how
  evidence is destroyed, not a record of a case where that was observed.

When a use contradicts something here, the use wins: change the file, keep the counter-example.
