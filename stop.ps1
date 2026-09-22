# Stop FlavorPilot by sending CTRL_BREAK to each process group, then wait.
# taskkill /F is used only when a process is still alive after that wait.

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not ("FlavorPilotProcess" -as [type])) {
  Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

public static class FlavorPilotProcess {
    const uint CTRL_BREAK_EVENT = 1;

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool AttachConsole(uint dwProcessId);

    [DllImport("kernel32.dll", SetLastError = true, ExactSpelling = true)]
    public static extern bool FreeConsole();

    [DllImport("kernel32.dll")]
    public static extern bool SetConsoleCtrlHandler(ConsoleCtrlDelegate HandlerRoutine, bool Add);

    public delegate bool ConsoleCtrlDelegate(uint CtrlType);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool GenerateConsoleCtrlEvent(uint dwCtrlEvent, uint dwProcessGroupId);

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

$script:Forced = $false
$script:Stopped = $false

function Test-FlavorPilotCommand {
  param([int]$ProcessId)
  $row = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
  if (-not $row) { return $false }
  $command = "$($row.Name) $($row.CommandLine)"
  return ($command -match "backend\.app\.main|python -m app\.main| app\.main|vite|npm")
}

function Stop-Gracefully {
  param([int]$ProcessId, [string]$Label, [switch]$FromPort)
  if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return }
  if (-not $FromPort -and -not (Test-FlavorPilotCommand -ProcessId $ProcessId)) {
    Write-Host "   Skipping pid $ProcessId; it is not a FlavorPilot process."
    return
  }
  Write-Host "   Sending CTRL_BREAK to $Label ($ProcessId)."
  try {
    [FlavorPilotProcess]::Break([uint32]$ProcessId)
  } catch {
    Write-Host "   CTRL_BREAK was not delivered ($($_.Exception.Message))."
  }
  $deadline = (Get-Date).AddSeconds(8)
  while ((Get-Date) -lt $deadline) {
    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
      Write-Host "   $Label exited after CTRL_BREAK."
      $script:Stopped = $true
      return
    }
    Start-Sleep -Milliseconds 250
  }
  Write-Host "   $Label is still running. Forcing stop."
  & taskkill.exe /PID $ProcessId /T /F | Out-Null
  $script:Forced = $true
  $script:Stopped = $true
}

function Stop-PidFile {
  param([string]$Name)
  $file = Join-Path $Root ".flavorpilot.$Name.pid"
  if (-not (Test-Path $file)) { return }
  $processId = 0
  [void][int]::TryParse((Get-Content $file -Raw).Trim(), [ref]$processId)
  if ($processId -gt 0) {
    Stop-Gracefully -ProcessId $processId -Label $Name
  }
  Remove-Item $file -Force -ErrorAction SilentlyContinue
}

function Stop-Port {
  param([int]$Port)
  $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($processId in $listeners) {
    Stop-Gracefully -ProcessId $processId -Label "port $Port" -FromPort
  }
}

Write-Host "Stopping FlavorPilot..."
Stop-PidFile -Name "backend"
Stop-PidFile -Name "frontend"
Stop-Port -Port 8000
Stop-Port -Port 8080
Stop-Port -Port 5173

if (-not $script:Stopped) {
  Write-Host "   No FlavorPilot processes found."
}
Write-Host ""
if ($script:Forced) {
  Write-Host "FlavorPilot stopped, but one process needed a forced kill."
  exit 1
}
Write-Host "FlavorPilot stopped."
Write-Host ""
