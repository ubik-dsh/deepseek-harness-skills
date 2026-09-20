# The readings, and what each one will not tell you

One command per reading, with the limit that is not visible from the value. Every one of these
is read-only. **The limits are the reason this file exists**: each command returns something
plausible whether or not it worked.

---

## The machine and its firmware

```powershell
Get-CimInstance Win32_ComputerSystem |
  Select-Object Manufacturer,Model,TotalPhysicalMemory,SystemType,PCSystemType
Get-CimInstance Win32_BIOS |
  Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate
```

**Two queries in one probe produce a two-element list**, `[0]` the system and `[1]` the
firmware. A caller that takes `[0]` and reads BIOS fields off it gets `None` for every one of
them — which is how this was discovered, on a machine whose manufacturer came back empty.

**`PCSystemType` is the field that tells you this is a virtual machine** — 1 is desktop, 2 is
mobile, and a value outside the documented set usually means a hypervisor. Diagnosing the
"hardware" of a VM describes the host's abstraction.

## The processor

```powershell
Get-CimInstance Win32_Processor |
  Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed,LoadPercentage
```

**`CurrentClockSpeed` is a snapshot and `LoadPercentage` is a lie on many machines.** Both are
sampled at the instant of the query and neither measures anything sustained. A throttling
question is not answered here, however tempting the fields look.

## Memory: two classes, and you need both

```powershell
Get-CimInstance Win32_PhysicalMemory |
  Select-Object BankLabel,DeviceLocator,Capacity,Speed,ConfiguredClockSpeed,PartNumber
Get-CimInstance Win32_PhysicalMemoryArray | Select-Object MemoryDevices,MaxCapacityEx
```

**The first lists the sticks that are installed; the second lists the slots that exist.**
Reading only the first hides an empty slot — and a machine with two sticks in the wrong two
slots runs in single channel while reporting its full capacity. **The interesting number is
`MemoryDevices` minus the stick count**, together with `DeviceLocator`: `Controller0-ChannelA`
and `Controller1-ChannelA` is dual channel, and two sticks both on `Controller0` is not.

**`Speed` is the rating; `ConfiguredClockSpeed` is the running speed.** They differ whenever the
memory is not at its rating — the common case, and where an expected-performance complaint
usually lives.

## Disks: three views that disagree

```powershell
Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,MediaType,BusType,Size,HealthStatus,OperationalStatus
Get-CimInstance Win32_DiskDrive | Select-Object Index,Model,InterfaceType,Size,Status,SerialNumber
Get-PhysicalDisk | Get-StorageReliabilityCounter
```

**`HealthStatus` is a field, not a test.** A controller that reports no SMART leaves it at its
default. `Healthy` from a drive whose attributes were never read means the field held its
default value, and that is not the same statement. **On the machine this was written on, both
NVMe disks report `Healthy` while the SMART read fails** — those two facts together are the
whole point of this file.

**`Get-StorageReliabilityCounter` is where the counters are** — temperature, read and write
errors, wear, power-on hours. It is not SMART attributes; it is Microsoft's abstraction over
whatever the drive offers. On many machines it fails outright with *Access to a CIM resource was
not available to the client*, which means **no reading taken**, not a healthy disk.

**`Win32_DiskDrive` and `Get-PhysicalDisk` are different views and disagree** about size,
identification and sometimes count — a USB enclosure or a RAID volume is one disk in one and
several in the other. Know which you asked before quoting a number.

**SMART attributes need a tool Windows does not ship.** `smartctl` from smartmontools is the
usual one: `-a` for everything, `-H` for the one-line verdict — and that verdict is a summary of
attributes, so it is only as good as their availability.

## Volumes

```powershell
Get-Volume | Where-Object DriveLetter |
  Select-Object DriveLetter,FileSystemLabel,FileSystem,HealthStatus,Size,SizeRemaining
```

**`HealthStatus` here is about the filesystem, not the disk.** A volume can be Healthy on a
drive that is failing, and a drive can be Healthy under a filesystem that is not.

## Graphics

```powershell
Get-CimInstance Win32_VideoController |
  Select-Object Name,DriverVersion,DriverDate,AdapterRAM,VideoModeDescription,Status
```

**`AdapterRAM` is a 32-bit field and wraps above 4 GB**, so a card with more reports a small or
negative number. It is not a capacity reading.

## Temperature: usually absent

```powershell
Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature
```

**On most machines this returns nothing, and on some it returns a number that is wrong.** Where
it answers, the value is tenths of a kelvin — `(value / 10) - 273.15`. Where it does not, the
correct conclusion is *no temperature was available*, and the next step is a vendor tool or
`HWiNFO`, not a different WMI class.

## Errors the machine wrote down

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-14)} -MaxEvents 40
```

**This is where a fault that leaves no other symptom shows up.** A machine that reboots with no
bugcheck has often written a WHEA error — provider `Microsoft-Windows-WHEA-Logger` — and a drive
that is going writes `disk` events before it fails. **A reboot clears the memory state, so read
this before restarting anything.**

`Level=1,2` is critical and error. Warnings are excluded deliberately: the System log carries
hundreds of benign ones and a report full of them buries the three that matter.

---

## The rule that applies to all of them

> **A missing reading is not a good reading.**

Every command above returns something plausible whether or not it worked. A disk says `Healthy`,
a query returns nothing, a tool is not installed and fails quietly. **The three-way split is the
finding** — a value, an empty answer, or an unavailable tool — and only the first is a reading.

`collect.py` prints the second and third separately, under a heading that says none of them is a
clean bill of health, because a report that lists only what it read is a report that says the
unread parts are fine.

---

## Where this came from

The frame — **symptom, evidence, hypothesis, test**; **read-only first**; an **escalation
ladder** — is taken from `Swietlik3d/windows-pc-skills`, a collection of 78 Windows-PC skills
found by a survey of 132 repositories. That collection is procedural prose in Polish with almost
no commands in it; its structure is the best thing in it, and it is used here.

The commands, the limits and the traps are ours, **verified on one machine** — which is not
many, and is why the list of absent readings is shorter than it should be. Every entry here was
either read or failed on that machine, and the failures are named.
