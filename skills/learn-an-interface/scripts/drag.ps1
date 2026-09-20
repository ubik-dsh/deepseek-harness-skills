param(
    [Parameter(Mandatory = $true)][int]$FromX,
    [Parameter(Mandatory = $true)][int]$FromY,
    [Parameter(Mandatory = $true)][int]$ToX,
    [Parameter(Mandatory = $true)][int]$ToY,
    [int]$Steps = 24,
    [int]$HoldMs = 220,
    [switch]$NoRelease
)

# A REAL drag: press, move in steps, release - through SendInput only.
#
# The traps this avoids, all measured in this family:
#   * `mouse_event` moved the pointer and drew NOTHING - zero pixels changed on a canvas. SendInput
#     is the only call that works.
#   * plain `SetCursorPos` is right about monitors and wrong about drags: it produces no move
#     events, so press and release land in one place and a stroke becomes a dot.
#   * a browser's drag-and-drop needs INTERMEDIATE moves. One jump from source to target is a
#     press and a release at two coordinates with nothing in between, and the page never sees a
#     drag at all - it sees a click that teleported.
#   * the button must be DOWN for the whole journey, so the moves carry MOUSEEVENTF_MOVE while
#     LEFTDOWN is already held, with no second press in the middle.

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
public struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr extra; }

[StructLayout(LayoutKind.Sequential)]
public struct INPUT { public uint type; public MOUSEINPUT mi; }

public class Drag {
    const uint MOVE = 0x0001, LEFTDOWN = 0x0002, LEFTUP = 0x0004;
    const uint ABSOLUTE = 0x8000, VIRTUALDESK = 0x4000;

    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint SendInput(uint n, INPUT[] inputs, int size);

    static INPUT At(int x, int y, uint extra) {
        int vx = GetSystemMetrics(76), vy = GetSystemMetrics(77);
        int vw = GetSystemMetrics(78), vh = GetSystemMetrics(79);
        INPUT one = new INPUT(); one.type = 0;
        one.mi.dx = (int)((long)(x - vx) * 65535 / (vw - 1));
        one.mi.dy = (int)((long)(y - vy) * 65535 / (vh - 1));
        one.mi.dwFlags = MOVE | ABSOLUTE | VIRTUALDESK | extra;
        return one;
    }

    public static uint Step(int x, int y, uint extra) {
        return SendInput(1, new INPUT[] { At(x, y, extra) }, Marshal.SizeOf(typeof(INPUT)));
    }
}
'@

$size = [System.Runtime.InteropServices.Marshal]::SizeOf([type]'INPUT')
Write-Output "  INPUT size $size"

# 1. Arrive at the source, with the button up, and settle. A drag that starts while the pointer is
#    still travelling begins on whatever it passes over.
[Drag]::Step($FromX, $FromY, 0) | Out-Null
Start-Sleep -Milliseconds 250

# 2. Press.
$sent = [Drag]::Step($FromX, $FromY, 0x0002)
Write-Output "  pressed at $FromX,$FromY ($sent of 1)"
Start-Sleep -Milliseconds $HoldMs

# 3. Move in steps. A small first move matters: the browser decides a drag has begun from the first
#    movement past its threshold, and a first step of 300 px can be read as a teleport.
for ($i = 1; $i -le $Steps; $i++) {
    $t = $i / $Steps
    $x = [int]($FromX + ($ToX - $FromX) * $t)
    $y = [int]($FromY + ($ToY - $FromY) * $t)
    [Drag]::Step($x, $y, 0) | Out-Null
    Start-Sleep -Milliseconds 28
}
Write-Output "  moved in $Steps steps to $ToX,$ToY with the button held"

# 4. Settle on the target before releasing, so the page can draw its insertion state.
Start-Sleep -Milliseconds $HoldMs
if ($NoRelease) {
    # Step 5 of the recorded logic: check the target SHOWS it will accept, before letting go.
    # Leaving the button down is the only way to look at that state.
    Write-Output "  HOLDING at $ToX,$ToY with the button down - -NoRelease was given"
    exit 0
}
$sent = [Drag]::Step($ToX, $ToY, 0x0004)
Write-Output "  released at $ToX,$ToY ($sent of 1)"
