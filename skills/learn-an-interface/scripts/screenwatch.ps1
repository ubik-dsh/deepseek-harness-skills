# screenwatch - record a demonstration so an agent can learn an interface from it.
#
# What it does
#   * captures at a chosen rate and writes numbered frames to a folder
#   * draws the real cursor with DrawIconEx, because CopyFromScreen does not include it, and
#     rings it in high contrast so it is visible on any background
#   * writes cursor.csv - frame, milliseconds, x, y - so the trajectory is readable as numbers
#     and the interesting frames can be picked rather than watched
#   * draws a thin red border with a live frame counter, so a recording is never mistaken for
#     nothing happening
#
# Why the cursor is ringed rather than recoloured: SetSystemCursor replaces the pointer for the
# whole session and every application, and it is easy to leave behind. A ring is drawn into the
# frame, changes nothing on the machine, and disappears with the process.
#
# The border window is click-through (WS_EX_TRANSPARENT) and never activates
# (WS_EX_NOACTIVATE), so a demonstration can be given through it.

param(
    [int]$Fps = 4,
    [string]$Out = "$env:TEMP\dsh-screenwatch",
    [int]$CropW = 1000,
    [int]$CropH = 700,
    [int]$Keep = 400,
    [int]$Seconds = 0,
    [switch]$Full
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# -ReferencedAssemblies, not just -AssemblyName above. Loading an assembly makes its types usable
# from PowerShell; it does NOT make the compiler reference it, and without this the C# fails with
# "the type or namespace name 'Drawing2D' does not exist in the namespace 'System.Drawing'
# (are you missing an assembly reference?)" - which reads like a missing .NET feature rather than
# a missing flag.
Add-Type -ReferencedAssemblies System.Drawing, System.Windows.Forms -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public class ScreenWatch : Form {
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] public struct CURSORINFO {
        public int cbSize; public int flags; public IntPtr hCursor; public POINT ptScreenPos; }

    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] static extern bool GetCursorInfo(ref CURSORINFO pci);
    [DllImport("user32.dll")] static extern bool DrawIconEx(IntPtr hdc, int x, int y, IntPtr hIcon,
        int cx, int cy, int istep, IntPtr hbr, int flags);
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int i);

    const int CURSOR_SHOWING = 0x0001;

    System.Windows.Forms.Timer timer;
    StreamWriter log;
    string outDir;
    int cropW, cropH, fps, keep, frames;
    bool fullScreen;
    int limitSeconds;
    DateTime start;

    public ScreenWatch(string dir, int fps, int cw, int ch, int keep, bool full, int seconds) {
        outDir = dir; this.fps = fps; cropW = cw; cropH = ch; this.keep = keep;
        fullScreen = full; limitSeconds = seconds;

        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.Manual;
        Bounds = new Rectangle(GetSystemMetrics(76), GetSystemMetrics(77),
                               GetSystemMetrics(78), GetSystemMetrics(79));
        TopMost = true;
        ShowInTaskbar = false;
        BackColor = Color.FromArgb(1, 2, 3);
        TransparencyKey = Color.FromArgb(1, 2, 3);
        DoubleBuffered = true;

        Directory.CreateDirectory(outDir);
        log = new StreamWriter(Path.Combine(outDir, "cursor.csv"));
        log.WriteLine("frame,ms,x,y");
        start = DateTime.UtcNow;

        timer = new System.Windows.Forms.Timer();
        timer.Interval = Math.Max(50, 1000 / fps);
        timer.Tick += delegate { Shot(); };
        timer.Start();
    }

    public int Frames { get { return frames; } }

    protected override CreateParams CreateParams {
        get {
            CreateParams cp = base.CreateParams;
            cp.ExStyle |= 0x20;         // WS_EX_TRANSPARENT   - clicks pass through
            cp.ExStyle |= 0x80;         // WS_EX_TOOLWINDOW    - not in alt-tab
            cp.ExStyle |= 0x08000000;   // WS_EX_NOACTIVATE    - never steals focus
            return cp;
        }
    }

    protected override void OnPaint(PaintEventArgs e) {
        Graphics g = e.Graphics;
        using (Pen pen = new Pen(Color.FromArgb(235, 24, 24), 3))
            g.DrawRectangle(pen, 1, 1, Width - 3, Height - 3);
        string label = "REC  " + frames.ToString() + " frames   " + fps + " fps";
        using (Font f = new Font("Consolas", 11, FontStyle.Bold)) {
            SizeF size = g.MeasureString(label, f);
            RectangleF box = new RectangleF(Width - size.Width - 34, 10, size.Width + 22, size.Height + 8);
            g.FillRectangle(Brushes.Black, box);
            g.DrawRectangle(Pens.Red, box.X, box.Y, box.Width, box.Height);
            g.DrawString(label, f, Brushes.White, box.X + 11, box.Y + 4);
        }
    }

    static void Ring(Graphics g, int x, int y) {
        // Black under, white over, magenta on top: readable on a white page and on a dark one.
        int r = 21;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        using (Pen p = new Pen(Color.Black, 7)) g.DrawEllipse(p, x - r, y - r, 2 * r, 2 * r);
        using (Pen p = new Pen(Color.White, 4)) g.DrawEllipse(p, x - r, y - r, 2 * r, 2 * r);
        using (Pen p = new Pen(Color.FromArgb(255, 0, 200), 3))
            g.DrawEllipse(p, x - r, y - r, 2 * r, 2 * r);
        using (Pen p = new Pen(Color.Black, 7)) {
            g.DrawLine(p, x - r - 13, y, x + r + 13, y);
            g.DrawLine(p, x, y - r - 13, x, y + r + 13);
        }
        using (Pen p = new Pen(Color.FromArgb(255, 0, 200), 3)) {
            g.DrawLine(p, x - r - 13, y, x + r + 13, y);
            g.DrawLine(p, x, y - r - 13, x, y + r + 13);
        }
    }

    void Shot() {
        frames++;

        POINT p; GetCursorPos(out p);
        int vx = GetSystemMetrics(76), vy = GetSystemMetrics(77);
        int vw = GetSystemMetrics(78), vh = GetSystemMetrics(79);

        int x, y, w, h;
        if (fullScreen) { x = vx; y = vy; w = vw; h = vh; }
        else {
            w = Math.Min(cropW, vw); h = Math.Min(cropH, vh);
            x = Math.Max(vx, Math.Min(p.X - w / 2, vx + vw - w));
            y = Math.Max(vy, Math.Min(p.Y - h / 2, vy + vh - h));
        }

        using (Bitmap bmp = new Bitmap(w, h))
        using (Graphics g = Graphics.FromImage(bmp)) {
            g.CopyFromScreen(x, y, 0, 0, new Size(w, h));

            // The real cursor, which CopyFromScreen leaves out.
            CURSORINFO ci = new CURSORINFO();
            ci.cbSize = Marshal.SizeOf(typeof(CURSORINFO));
            if (GetCursorInfo(ref ci) && ci.flags == CURSOR_SHOWING) {
                IntPtr hdc = g.GetHdc();
                DrawIconEx(hdc, p.X - x, p.Y - y, ci.hCursor, 0, 0, 0, IntPtr.Zero, 3);
                g.ReleaseHdc(hdc);
            }
            Ring(g, p.X - x, p.Y - y);

            // The frame carries its own marker. The overlay's red border is drawn on the screen,
            // not into the picture - and a cursor-centred crop does not reach the screen edge, so
            // the first version produced frames that looked like ordinary screenshots. A frame
            // that could be mistaken for a screenshot is a frame whose provenance is unknown.
            using (Pen pen = new Pen(Color.FromArgb(235, 24, 24), 3))
                g.DrawRectangle(pen, 1, 1, w - 3, h - 3);
            string stamp = "REC " + frames.ToString() + "   "
                         + ((int)(DateTime.UtcNow - start).TotalSeconds).ToString() + "s   "
                         + p.X.ToString() + "," + p.Y.ToString();
            using (Font f = new Font("Consolas", 10, FontStyle.Bold)) {
                SizeF size = g.MeasureString(stamp, f);
                RectangleF box = new RectangleF(6, 6, size.Width + 14, size.Height + 6);
                g.FillRectangle(Brushes.Black, box);
                g.DrawString(stamp, f, Brushes.White, box.X + 7, box.Y + 3);
            }

            bmp.Save(Path.Combine(outDir, string.Format("frame_{0:D6}.png", frames)), ImageFormat.Png);
        }

        log.WriteLine(frames + "," + ((int)(DateTime.UtcNow - start).TotalMilliseconds) + ","
                      + p.X + "," + p.Y);
        log.Flush();
        Invalidate();

        if (keep > 0 && frames > keep) {
            string old = Path.Combine(outDir, string.Format("frame_{0:D6}.png", frames - keep));
            if (File.Exists(old)) { try { File.Delete(old); } catch { } }
        }
        if (limitSeconds > 0 && (DateTime.UtcNow - start).TotalSeconds >= limitSeconds) {
            timer.Stop();
            log.Close();
            Application.Exit();
        }
    }
}
'@

Write-Output "  output : $Out"
Write-Output "  rate   : $Fps fps   region: $(if ($Full) { 'the whole desktop' } else { "${CropW}x${CropH} around the cursor" })"
Write-Output "  limit  : $(if ($Seconds -gt 0) { "$Seconds seconds" } else { 'until stopped' })"
Write-Output ""
Write-Output "  A red border is drawn round the screen with the frame count on it."
Write-Output "  Stop it by closing this window, or kill the process."
Write-Output ""

$watch = New-Object ScreenWatch($Out, $Fps, $CropW, $CropH, $Keep, [bool]$Full, $Seconds)
[System.Windows.Forms.Application]::Run($watch)
Write-Output "  stopped after $($watch.Frames) frames"
