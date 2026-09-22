# Start FlavorPilot and record process-group leaders so stop.ps1 can
# shut both servers down with a console break, not a forced kill.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
New-Item -ItemType Directory -Force -Path (Join-Path $Root ".run") | Out-Null

Write-Host "Starting FlavorPilot..."

if (-not ("FlavorPilotProcess" -as [type])) {
  Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

public static class FlavorPilotProcess {
    const uint CREATE_NEW_PROCESS_GROUP = 0x00000200;
    const uint CTRL_BREAK_EVENT = 1;

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {
        public int cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public int dwX;
        public int dwY;
        public int dwXSize;
        public int dwYSize;
        public int dwXCountChars;
        public int dwYCountChars;
        public int dwFillAttribute;
        public int dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {
        public IntPtr hProcess;
        public IntPtr hThread;
        public int dwProcessId;
        public int dwThreadId;
    }

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateProcess(
        string lpApplicationName,
        string lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        bool bInheritHandles,
        uint dwCreationFlags,
        IntPtr lpEnvironment,
        string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo,
        out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool AttachConsole(uint dwProcessId);

    [DllImport("kernel32.dll", SetLastError = true, ExactSpelling = true)]
    public static extern bool FreeConsole();

    [DllImport("kernel32.dll")]
    public static extern bool SetConsoleCtrlHandler(ConsoleCtrlDelegate HandlerRoutine, bool Add);

    public delegate bool ConsoleCtrlDelegate(uint CtrlType);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool GenerateConsoleCtrlEvent(uint dwCtrlEvent, uint dwProcessGroupId);

    public static int Start(string commandLine, string workingDirectory) {
        STARTUPINFO si = new STARTUPINFO();
        si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
        PROCESS_INFORMATION pi;
        bool ok = CreateProcess(null, commandLine, IntPtr.Zero, IntPtr.Zero, false, CREATE_NEW_PROCESS_GROUP, IntPtr.Zero, workingDirectory, ref si, out pi);
        if (!ok) {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        int pid = pi.dwProcessId;
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        return pid;
    }

    public static void Break(uint pid) {
        FreeConsole();
        if (!AttachConsole(pid)) {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        SetConsoleCtrlHandler(null, true);
        try {
            if (!GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, pid)) {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
        } finally {
            FreeConsole();
            SetConsoleCtrlHandler(null, false);
        }
    }
}
"@
}

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $python) {
  throw "Python was not found."
}

function Start-RecordedProcess {
  param([string]$Name, [string]$CommandLine)
  $processId = [FlavorPilotProcess]::Start($CommandLine, $Root)
  Set-Content -Path (Join-Path $Root ".flavorpilot.$Name.pid") -Value $processId
  Write-Host "   $Name pid $processId"
}

Write-Host "Starting the API..."
Start-RecordedProcess -Name "backend" -CommandLine "`"$python`" -m backend.app.main"

$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm) { $npm = (Get-Command npm -ErrorAction SilentlyContinue).Source }
if (-not $npm) { throw "npm was not found." }
Write-Host "Starting the frontend..."
Start-RecordedProcess -Name "frontend" -CommandLine "cmd.exe /c `"$npm`" run dev"

Write-Host "Waiting for the API and the frontend..."
$backendReady = $false
$frontendReady = $false
$frontendUrl = "http://localhost:8080"
foreach ($attempt in 1..40) {
  if (-not $backendReady) {
    try {
      Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
      $backendReady = $true
    } catch {}
  }
  if (-not $frontendReady) {
    foreach ($url in @("http://127.0.0.1:8080", "http://127.0.0.1:5173")) {
      try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 | Out-Null
        $frontendReady = $true
        $frontendUrl = $url -replace "127.0.0.1", "localhost"
        break
      } catch {}
    }
  }
  if ($backendReady -and $frontendReady) { break }
  Start-Sleep -Milliseconds 500
}

Write-Host ""
if ($backendReady -and $frontendReady) {
  Write-Host "FlavorPilot is running."
} else {
  Write-Host "FlavorPilot did not finish starting."
}
Write-Host "   Frontend:    $frontendUrl"
Write-Host "   Backend API: http://localhost:8000"
Write-Host "   API docs:    http://localhost:8000/docs"
Write-Host ""
Write-Host "Stop both servers with ./stop.ps1"
