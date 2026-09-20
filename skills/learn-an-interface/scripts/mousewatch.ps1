param(
    [string]$Out = "",
    [int]$Seconds = 60,
    [switch]$Quiet
)

# Every mouse event, as it happens, with the button named.
#
# WHY A HOOK AND NOT A POLL. The screen recorder polls the pointer five times a second, which is right
# for pictures and wrong for input: at five samples a second a drag is three to five samples, and a
# click can fall entirely between two of them. A low-level mouse hook (WH_MOUSE_LL) receives EVERY
# event the system delivers - every press, every release, every wheel notch - with its coordinates and
# its own timestamp. Nothing is sampled and nothing is missed.
#
# AND IT CALIBRATES ITSELF. A mouse does not announce how many buttons it has or what its side buttons
# send; SM_CMOUSEBUTTONS reports a count and nothing about identity. So this prints what actually
# arrives as each button is pressed, which is the measurement rather than the assumption.
#
# The hook MUST call CallNextHookEx and MUST return quickly: a low-level hook runs on the thread that
# installed it and every event in the system waits for it. The callback here appends one string and
# returns.
#
# ASCII only: Windows PowerShell 5.1 reads a .ps1 with no byte-order mark as CP1251.

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class MouseWatch {
    public const int WH_MOUSE_LL = 14;

    public const int WM_MOUSEMOVE      = 0x0200;
    public const int WM_LBUTTONDOWN    = 0x0201;
    public const int WM_LBUTTONUP      = 0x0202;
    public const int WM_RBUTTONDOWN    = 0x0204;
    public const int WM_RBUTTONUP      = 0x0205;
    public const int WM_MBUTTONDOWN    = 0x0207;
    public const int WM_MBUTTONUP      = 0x0208;
    public const int WM_MOUSEWHEEL     = 0x020A;
    public const int WM_XBUTTONDOWN    = 0x020B;
    public const int WM_XBUTTONUP      = 0x020C;
    public const int WM_MOUSEHWHEEL    = 0x020E;

    [StructLayout(LayoutKind.Sequential)]
    public struct MSLLHOOKSTRUCT {
        public int ptX, ptY;
        public uint mouseData, flags, time;
        public IntPtr dwExtraInfo;
    }

    public delegate IntPtr LowLevelProc(int nCode, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr SetWindowsHookEx(int idHook, LowLevelProc proc, IntPtr hMod, uint threadId);
    [DllImport("user32.dll", SetLastError = true)]
    static extern bool UnhookWindowsHookEx(IntPtr hook);
    [DllImport("user32.dll")]
    static extern IntPtr CallNextHookEx(IntPtr hook, int nCode, IntPtr wParam, IntPtr lParam);
    [DllImport("kernel32.dll")]
    static extern IntPtr GetModuleHandle(string name);
    [DllImport("user32.dll")]
    public static extern int GetSystemMetrics(int index);

    static IntPtr hook = IntPtr.Zero;
    static LowLevelProc proc;
    static readonly object gate = new object();
    static List<string> pending = new List<string>();
    static DateTime start = DateTime.UtcNow;

    public static bool Running { get { return hook != IntPtr.Zero; } }

    public static string Name(int message) {
        switch (message) {
            case WM_MOUSEMOVE:   return "move";
            case WM_LBUTTONDOWN: return "L-down";
            case WM_LBUTTONUP:   return "L-up";
            case WM_RBUTTONDOWN: return "R-down";
            case WM_RBUTTONUP:   return "R-up";
            case WM_MBUTTONDOWN: return "M-down";
            case WM_MBUTTONUP:   return "M-up";
            case WM_XBUTTONDOWN: return "X-down";
            case WM_XBUTTONUP:   return "X-up";
            case WM_MOUSEWHEEL:  return "wheel";
            case WM_MOUSEHWHEEL: return "hwheel";
        }
        return "0x" + message.ToString("X4");
    }

    static IntPtr OnEvent(int nCode, IntPtr wParam, IntPtr lParam) {
        if (nCode >= 0) {
            MSLLHOOKSTRUCT data = (MSLLHOOKSTRUCT)Marshal.PtrToStructure(lParam, typeof(MSLLHOOKSTRUCT));
            int message = (int)wParam;
            string detail = "";
            if (message == WM_XBUTTONDOWN || message == WM_XBUTTONUP) {
                int which = (int)((data.mouseData >> 16) & 0xFFFF);
                detail = (which == 1) ? "X1(back)" : (which == 2) ? "X2(forward)" : ("X" + which);
            } else if (message == WM_MOUSEWHEEL || message == WM_MOUSEHWHEEL) {
                short delta = (short)((data.mouseData >> 16) & 0xFFFF);
                detail = (delta > 0 ? "+" : "") + (delta / 120).ToString();
            }
            if (message != WM_MOUSEMOVE) {
                int ms = (int)(DateTime.UtcNow - start).TotalMilliseconds;
                string line = ms + "," + Name(message) + "," + data.ptX + "," + data.ptY + "," + detail;
                lock (gate) { pending.Add(line); }
            }
        }
        return CallNextHookEx(hook, nCode, wParam, lParam);
    }

    public static bool Start() {
        proc = new LowLevelProc(OnEvent);
        hook = SetWindowsHookEx(WH_MOUSE_LL, proc, GetModuleHandle(null), 0);
        start = DateTime.UtcNow;
        return hook != IntPtr.Zero;
    }

    public static void Stop() {
        if (hook != IntPtr.Zero) { UnhookWindowsHookEx(hook); hook = IntPtr.Zero; }
    }

    public static string[] Take() {
        lock (gate) {
            string[] taken = pending.ToArray();
            pending.Clear();
            return taken;
        }
    }
}
'@ -ReferencedAssemblies System.Windows.Forms, System.Drawing

Write-Output ""
Write-Output "  === the mouse, as Windows describes it"
Write-Output "    GetSystemMetrics(SM_CMOUSEBUTTONS) = $([MouseWatch]::GetSystemMetrics(43))"
Write-Output "    (43 is SM_CMOUSEBUTTONS: the COUNT of buttons, and nothing about which is which)"
Write-Output ""
Write-Output "  READY - every button press, release and wheel notch is logged from now on."
Write-Output "  Press each button once, slowly, starting with the left."
Write-Output "  Running for $Seconds seconds. Close the hidden window or Ctrl+C to stop early."
Write-Output ""
Write-Output "    ms      event     x     y   detail"
Write-Output "  -------  --------  ----  ----  -------"

# A LOW-LEVEL HOOK NEEDS A MESSAGE LOOP ON THE THREAD THAT INSTALLED IT.
#
# The first version installed the hook and then sat in a `while` loop with Start-Sleep, and recorded
# NOTHING at all: SetWindowsHookEx delivers callbacks by posting messages to the installing thread, so
# without a pump the procedure is never called and the hook is a silent no-op. It reports success, the
# events do not arrive, and there is no error to notice.
#
# A hidden form with Application.Run IS a message loop, and a timer on the same thread does the
# logging. The form is parked off-screen: it exists to own the pump, not to be seen.
$writer = $null
if ($Out -ne "") {
    $writer = New-Object System.IO.StreamWriter($Out, $false, [System.Text.Encoding]::UTF8)
    $writer.WriteLine("ms,event,x,y,detail")
    Write-Output "  logging to $Out"
}

$form = New-Object System.Windows.Forms.Form
$form.ShowInTaskbar = $false
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.Location = New-Object System.Drawing.Point(-3000, -3000)
$form.Size = New-Object System.Drawing.Size(10, 10)

$script:count = 0
$deadline = (Get-Date).AddSeconds($Seconds)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 120
$timer.Add_Tick({
    foreach ($line in [MouseWatch]::Take()) {
        $parts = $line.Split(",")
        # Console::WriteLine, not Write-Output: output written from a WinForms timer callback does
        # not reach PowerShell's pipeline, so the first version counted fifteen events, logged them
        # to the file, and printed NONE of them. Console goes straight to the process's stdout and
        # arrives wherever the process was started from.
        [Console]::WriteLine(("  {0,7}  {1,-8}  {2,4}  {3,4}  {4}" -f $parts[0], $parts[1], $parts[2], $parts[3], $parts[4]))
        if ($script:writer) { $script:writer.WriteLine($line) }
        $script:count++
    }
    if ((Get-Date) -ge $script:deadline) {
        $script:timer.Stop()
        $script:form.Close()
    }
})

$form.Add_Shown({
    if (-not [MouseWatch]::Start()) {
        Write-Output "  FAILED to install the mouse hook"
        $script:form.Close()
        return
    }
    $script:timer.Start()
})
$form.Add_FormClosed({
    [MouseWatch]::Stop()
    $script:timer.Stop()
})

[System.Windows.Forms.Application]::Run($form)
$timer.Dispose(); $form.Dispose()

if ($writer) { $writer.Flush(); $writer.Close() }
Write-Output ""
Write-Output "  $($script:count) event(s) recorded. The hook is removed."
