param(
    [string]$PlexToken = "",
    [string]$PlexUrl = "http://localhost:32400",
    [string]$TargetLang = "he",
    [string]$SourceLang = "en",
    [int]$PollInterval = 15
)

$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) {
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        return $false
    }
    return $true
}

Write-Info 'Checking Python 3...'
if (-not (Require-Command 'python')) {
    Write-Host 'Python 3 was not found. Please install it from https://www.python.org/downloads/windows/' -ForegroundColor Red
    exit 1
}

$PythonExe = (Get-Command python).Source
Write-Info "Using Python: $PythonExe"

Write-Info 'Checking ffmpeg...'
if (-not (Require-Command 'ffmpeg')) {
    Write-Warn 'ffmpeg was not found on PATH. Install it from https://www.ffmpeg.org/download.html and re-run this script.'
}

Write-Info 'Installing plex-auto-subs and dependencies...'
& $PythonExe -m pip install --upgrade "git+https://github.com/roies/plex-auto-subs" ffsubsync argostranslate

$ScriptsDir = & $PythonExe -c "import sysconfig; print(sysconfig.get_path('scripts'))"
$DaemonPath = Join-Path $ScriptsDir 'plex-auto-subs.exe'
if (-not (Test-Path $DaemonPath)) {
    $DaemonPath = Join-Path $env:APPDATA 'Python\Python312\Scripts\plex-auto-subs.exe'
}

if (-not $PlexToken) {
    $PlexToken = Read-Host 'Enter your Plex token (leave blank for local no-auth)'
}
if (-not $PlexUrl) {
    $PlexUrl = Read-Host 'Plex URL [http://localhost:32400]'
}
if (-not $PlexUrl) { $PlexUrl = 'http://localhost:32400' }

$EnvDir = Join-Path $env:ProgramData 'plex-auto-subs'
New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
$EnvFile = Join-Path $EnvDir 'settings.env'
@"
PLEX_URL=$PlexUrl
PLEX_TOKEN=$PlexToken
TARGET_LANG=$TargetLang
SOURCE_LANG=$SourceLang
POLL_INTERVAL=$PollInterval
"@ | Set-Content -Path $EnvFile -Encoding utf8

Write-Info "Wrote environment file to $EnvFile"

$TaskName = 'plex-auto-subs'
$TaskAction = New-ScheduledTaskAction -Execute $DaemonPath -Argument ''
$TaskTrigger = New-ScheduledTaskTrigger -AtStartup
$TaskPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest
$TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingToSleep
Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $TaskTrigger -Principal $TaskPrincipal -Settings $TaskSettings -Force | Out-Null

Write-Host ''
Write-Info 'Installation complete.'
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Cyan
Write-Host '  - Start the task: Start-ScheduledTask -TaskName plex-auto-subs'
Write-Host '  - Check logs: Get-ScheduledTaskInfo -TaskName plex-auto-subs'
Write-Host '  - Edit settings: notepad.exe "' + $EnvFile + '"'
Write-Host ''
Write-Warn 'Use this tool only for lawful personal/home use and only with media/subtitles you are authorized to access.'
