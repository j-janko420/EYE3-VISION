# EYE3 Box installer for Windows. Double-click install.bat, or run:
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-DryRun] [-Uninstall] [-Kiosk] [-Dir C:\folder]
# By default only EYE3 Link is installed (it starts at every sign-in) plus an "EYE3 Home" link on the Desktop that opens
# in your normal browser, so your saved lists, accounts and settings are untouched. -Kiosk is for the box behind a TV:
# it also opens EYE3 Home fullscreen at every sign-in.
# Needs no internet when this folder already holds eye3-link-windows.exe (or eye3-link.py with Python installed).
# Otherwise it downloads the program from the EYE3 release page and checks its SHA-256 first.
param([switch]$DryRun, [switch]$Uninstall, [switch]$Kiosk, [string]$Dir = "")
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Dir) { $Dir = Join-Path $env:LOCALAPPDATA "EYE3" }
$Rel = "https://github.com/j-janko420/EYE3-VISION/releases/download/eye3-link-latest"
$Asset = "eye3-link-windows.exe"
$Startup = [Environment]::GetFolderPath("Startup")
$LinkLnk = Join-Path $Startup "EYE3 Link.lnk"
$HomeLnk = Join-Path $Startup "EYE3 Home.lnk"
$Desktop = [Environment]::GetFolderPath("Desktop")
$DeskUrl = Join-Path $Desktop "EYE3 Home.url"
function Say($t) { Write-Host $t }
function Act($what, [scriptblock]$do) { if ($DryRun) { Say "[dry-run] $what" } else { & $do } }

if ($Uninstall) {
  Say "Removing the EYE3 start-up entries (the folder $Dir and your playlists stay)."
  Act "remove $LinkLnk and $HomeLnk" { Remove-Item -Force -ErrorAction SilentlyContinue $LinkLnk, $HomeLnk, $DeskUrl }
  exit 0
}

Say "EYE3 Box install into $Dir"
Act "create $Dir\playlists" { New-Item -ItemType Directory -Force -Path (Join-Path $Dir "playlists") | Out-Null }

# 1. the program: the one on this stick, else the Python file, else a checked download
$Local = Join-Path $Here $Asset
$Py = Join-Path $Here "eye3-link.py"
if (Test-Path $Local) {
  Say "Program: $Asset from this folder"
  Act "copy $Asset" { Copy-Item -Force $Local (Join-Path $Dir "eye3-link.exe") }
} elseif ((Test-Path $Py) -and (Get-Command python -ErrorAction SilentlyContinue)) {
  Say "Program: eye3-link.py (runs with Python; it cannot update itself)"
  Act "copy eye3-link.py" { Copy-Item -Force $Py (Join-Path $Dir "eye3-link.py") }
} elseif ($DryRun) {
  Say "[dry-run] would download $Asset from $Rel and check its SHA-256"
} else {
  Say "Downloading $Asset from the EYE3 release page..."
  $Tmp = Join-Path ([IO.Path]::GetTempPath()) ("eye3-" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $Tmp | Out-Null
  try {
    Invoke-WebRequest -UseBasicParsing "$Rel/$Asset" -OutFile (Join-Path $Tmp $Asset)
    Invoke-WebRequest -UseBasicParsing "$Rel/SHA256SUMS.txt" -OutFile (Join-Path $Tmp "SHA256SUMS.txt")
  } catch {
    Say "Download failed. Check the internet, or copy the kit with the program onto the stick."
    exit 1
  }
  $Want = ""
  foreach ($line in Get-Content (Join-Path $Tmp "SHA256SUMS.txt")) { if ($line -match "^([0-9a-fA-F]{64})\s+\*?$([regex]::Escape($Asset))\s*$") { $Want = $Matches[1] } }
  $Got = (Get-FileHash -Algorithm SHA256 (Join-Path $Tmp $Asset)).Hash
  if (-not $Want -or $Want -ne $Got) { Say "The download does not match its published SHA-256. Not installed."; Remove-Item -Recurse -Force $Tmp; exit 1 }
  Copy-Item -Force (Join-Path $Tmp $Asset) (Join-Path $Dir "eye3-link.exe")
  Remove-Item -Recurse -Force $Tmp
  Say "Checked SHA-256: ok"
}

# 2. settings, launchers, the viewer's own playlists
$Conf = Join-Path $Dir "eye3-link.conf"
if (-not (Test-Path $Conf)) { Act "write eye3-link.conf" { Copy-Item (Join-Path $Here "eye3-link.conf.example") $Conf } }
foreach ($f in "eye3-start.bat", "eye3-browser.bat") { Act "copy $f" { Copy-Item -Force (Join-Path $Here $f) (Join-Path $Dir $f) } }
$PlSrc = Join-Path $Here "playlists"
if (Test-Path $PlSrc) {
  foreach ($f in Get-ChildItem $PlSrc -File | Where-Object { $_.Extension -in ".m3u", ".m3u8", ".txt" }) {
    $to = Join-Path (Join-Path $Dir "playlists") $f.Name
    if ($f.Name -ne "README.txt") { Say "Playlist: $($f.Name)" }
    if (-not (Test-Path $to)) { Act "copy playlist $($f.Name)" { Copy-Item $f.FullName $to } }
  }
}

# 3. start at every sign-in, and start now
function MakeShortcut($path, $target) {
  $sh = New-Object -ComObject WScript.Shell
  $s = $sh.CreateShortcut($path)
  $s.TargetPath = $target
  $s.WorkingDirectory = $Dir
  $s.WindowStyle = 7
  $s.Save()
}
if ($env:EYE3_NO_SERVICE -eq "1") {
  Say "Skipping the start-up entries (EYE3_NO_SERVICE=1)."
} else {
  Say "Start-up: EYE3 Link at every sign-in (restarts by itself)"
  Act "create $LinkLnk and the Desktop link $DeskUrl" {
    MakeShortcut $LinkLnk (Join-Path $Dir "eye3-start.bat")
    Set-Content -Path $DeskUrl -Value "[InternetShortcut]`r`nURL=https://j-janko420.github.io/EYE3-VISION/home/?splash=0&box=1"
  }
  if ($Kiosk) {
    Say "Kiosk: EYE3 Home fullscreen at every sign-in"
    Act "create $HomeLnk" { MakeShortcut $HomeLnk (Join-Path $Dir "eye3-browser.bat") }
  }
  Act "start EYE3 Link now" { Start-Process -WindowStyle Minimized (Join-Path $Dir "eye3-start.bat") }
  if ($Kiosk) { Act "open EYE3 Home fullscreen now" { Start-Process -WindowStyle Minimized (Join-Path $Dir "eye3-browser.bat") } }
  else { Say "Open EYE3 Home from the 'EYE3 Home' link on your Desktop (it opens in your normal browser)." }
}
Say ""
Say "Done. EYE3 Link runs by itself at every sign-in and updates itself. To undo: install.bat -Uninstall"
Say "Your own playlists go into: $(Join-Path $Dir 'playlists')"
