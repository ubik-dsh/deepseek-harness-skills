#!/usr/bin/env python3
"""Read a Windows machine's hardware, and mark every reading that was not taken.

The rule this exists to enforce: **a missing reading is not a good reading.** A disk reports
`Healthy` whether it was checked or not; a temperature query returns nothing on most machines;
a tool that is not installed fails quietly if you are not looking. Every one of those reads as
"fine" to anyone skimming a report.

So each probe lands in one of three states and the report says which:

    value        the machine answered
    empty        it was asked and did not answer - THIS IS NOT HEALTH
    unavailable  the tool is absent or the rights are insufficient

It changes nothing. No repair, no update, no setting. Read-only, as the skill requires: the
cheap repair destroys the evidence for the expensive fault.

    python collect.py                    everything readable, as JSON
    python collect.py --only disk,memory
    python collect.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone

# name, what it reads, and the PowerShell that reads it. Every command here is read-only:
# Get-* , a WMI class query, or powercfg /batteryreport which writes a file and touches
# nothing about the machine's state.
PROBES: list[tuple[str, str, str]] = [
    # ONE ConvertTo-Json over one object. Two calls joined by a semicolon emit two JSON
    # documents, which nothing parses - and the fallback then looked like a reading.
    ("system", "the machine, its firmware and its age",
     "[pscustomobject]@{ "
     "system = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,"
     "TotalPhysicalMemory,NumberOfProcessors,SystemType,PCSystemType; "
     "bios = Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,"
     "ReleaseDate,SerialNumber } | ConvertTo-Json -Depth 5"),
    ("processor", "the processor as the firmware describes it",
     "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,"
     "MaxClockSpeed,CurrentClockSpeed,L3CacheSize,LoadPercentage | ConvertTo-Json -Depth 4"),
    # The two memory classes are separate on purpose: one lists the sticks, the other lists
    # the SLOTS. Reading only the first hides an empty slot and a machine in single channel.
    ("memory", "the sticks that are installed",
     "Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel,DeviceLocator,Capacity,"
     "Speed,ConfiguredClockSpeed,Manufacturer,PartNumber | ConvertTo-Json -Depth 4"),
    ("memory-slots", "how many slots exist, and how many are free",
     "Get-CimInstance Win32_PhysicalMemoryArray | Select-Object MemoryDevices,"
     "MaxCapacityEx | ConvertTo-Json -Depth 4"),
    ("disk", "every physical disk, its bus and the health FIELD",
     "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,MediaType,BusType,Size,HealthStatus,"
     "OperationalStatus | ConvertTo-Json -Depth 4"),
    ("disk-wmi", "the same disks as WMI sees them, which is a different view",
     "Get-CimInstance Win32_DiskDrive | Select-Object Index,Model,InterfaceType,Size,Status,"
     "SerialNumber,Partitions | ConvertTo-Json -Depth 4"),
    ("volume", "volumes, filesystems and free space",
     "Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,FileSystemLabel,"
     "FileSystem,HealthStatus,Size,SizeRemaining | ConvertTo-Json -Depth 4"),
    ("gpu", "display adapters and their drivers",
     "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,"
     "AdapterRAM,VideoModeDescription,Status | ConvertTo-Json -Depth 4"),
    # Usually absent. MSAcpi_ThermalZoneTemperature answers on some machines and returns a
    # plausible wrong number on others; absence is the common case.
    # No try/catch. The first version swallowed the error and returned an empty string, so
    # an access-denied refusal arrived as "the machine returned nothing" - the same
    # conflation the refusal handling exists to prevent, committed one layer below it. Let
    # the error reach the runner, which can tell the two apart.
    ("thermal", "thermal zones, where the firmware exposes any",
     "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
     "-ErrorAction Stop | Select-Object InstanceName,CurrentTemperature | ConvertTo-Json -Depth 4"),
    ("smart", "per-disk reliability counters, which are not SMART attributes",
     "Get-PhysicalDisk | ForEach-Object { $_ | Get-StorageReliabilityCounter | "
     "Select-Object DeviceId,Temperature,ReadErrorsTotal,WriteErrorsTotal,Wear,PowerOnHours } | "
     "ConvertTo-Json -Depth 4"),
    ("errors", "hardware errors the machine wrote down",
     "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; "
     "StartTime=(Get-Date).AddDays(-14)} -MaxEvents 40 -ErrorAction SilentlyContinue | "
     "Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,Message | ConvertTo-Json -Depth 4"),
]


def powershell() -> str | None:
    for candidate in ("powershell.exe", "pwsh.exe", "powershell", "pwsh"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def run(shell: str, script: str, timeout: int = 90) -> tuple[object | None, str]:
    """Run one probe. Returns whatever parsed, and why it did not when it did not."""
    try:
        result = subprocess.run(
            [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    except OSError as trouble:
        return None, f"could not run: {trouble}"

    text = (result.stdout or "").strip()
    if text == "":
        # The interesting case, and the one a careless report calls "fine".
        #
        # A refusal and an absence are different and must not be merged. A sensor the
        # firmware does not expose is a property of the machine; a query refused for want
        # of rights is a property of how it was asked, and it has a different fix. The
        # first version of this called an access-denied failure "the machine returned
        # nothing", which sends the reader to the wrong place.
        detail = " ".join((result.stderr or "").strip().split())
        lowered = detail.lower()
        if any(marker in lowered for marker in
               ("отказано в доступе", "access is denied", "access denied",
                "not available to the client", "privilege", "elevation")):
            return None, f"REFUSED, not absent - the query needs rights this session does " \
                         f"not have: {detail[:130]}"
        if detail:
            return None, detail[:160]
        return None, "the machine returned nothing for this"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Emphatically NOT a reading. The first version of this returned the raw text as a
        # value, the collector printed it as taken, and every field read off it was None.
        # A blob nobody can index belongs with the readings that were not taken.
        return None, ("the output was not one JSON document - two commands in a probe each "
                      "emit their own; the first 120 characters were: "
                      f"{text[:120].replace(chr(10), ' ')}")
    # ConvertTo-Json emits an object when the query found exactly one record and an array
    # when it found several. A caller indexing [0] works on this machine and breaks on the
    # next one, so the shape is fixed here instead of being left for the reader to guess.
    return (parsed if isinstance(parsed, list) else [parsed]), ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default="", help="comma-separated probe names")
    parser.add_argument("--json", type=str, default="", help="write the report here")
    args = parser.parse_args()

    shell = powershell()
    if shell is None:
        print("  no PowerShell found; this reads a Windows machine", file=sys.stderr)
        return 2

    wanted = {name.strip() for name in args.only.split(",") if name.strip()}
    probes = [probe for probe in PROBES if not wanted or probe[0] in wanted]
    if not probes:
        print(f"  none of {sorted(wanted)} is a probe; try: "
              f"{', '.join(name for name, _, _ in PROBES)}", file=sys.stderr)
        return 2

    report: dict = {
        "read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": {},
        "readings": {},
        "not_read": {},
    }

    for name, what, script in probes:
        value, why = run(shell, script)
        if value is None:
            report["not_read"][name] = {"what": what, "why": why}
            print(f"  --  {name:14} NOT READ   {why[:66]}")
        else:
            empty = value in ([], {}, "", None)
            report["readings"][name] = {"what": what, "value": value}
            if empty:
                # A structured answer that contains nothing is still an answer of nothing.
                report["not_read"][name] = {"what": what, "why": "returned no records"}
                print(f"  --  {name:14} EMPTY      the query succeeded and found nothing")
                del report["readings"][name]
            else:
                count = len(value) if isinstance(value, list) else 1
                print(f"  ok  {name:14} {count} record(s)")

    print()
    read = len(report["readings"])
    missing = len(report["not_read"])
    print(f"  {read} reading(s) taken, {missing} not taken")
    if missing:
        print()
        refused = [pair for pair in report["not_read"].items()
                   if pair[1]["why"].startswith("REFUSED")]
        if refused:
            print(f"  Of those, {len(refused)} were REFUSED for want of rights rather than "
                  "absent from the machine.")
            print("  An unelevated session cannot read them; that is a different fact about "
                  "the machine than a sensor it does not have.")
            print()
        print("  NOT TAKEN, and none of these is a clean bill of health:")
        for name, detail in report["not_read"].items():
            print(f"    {name:14} {detail['what']}")
            print(f"    {'':14} {detail['why'][:88]}")
    print()
    print("  A component that was not read is not a component that is fine.")

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print(f"  written to {args.json}")
    else:
        print()
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
