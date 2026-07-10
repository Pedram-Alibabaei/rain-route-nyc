param(
    [int]$Year = 2025,
    [int[]]$Months = @(1, 7, 12),
    [int]$Limit = 200000,
    [int]$DashboardPort = 8501,
    [switch]$SkipInstall,
    [switch]$SkipImportIfEmpty,
    [switch]$ForceImport,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Benötigter Befehl nicht gefunden: $Name"
    }
}

function Invoke-Checked {
    param(
        [scriptblock]$Command,
        [string]$ErrorMessage
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

function Test-DockerReady {
    try {
        docker info *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Get-DockerDesktopPath {
    $candidates = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:LocalAppData "Docker\Docker Desktop.exe")
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Start-DockerDesktopIfNeeded {
    param([int]$TimeoutSeconds = 240)

    if (Test-DockerReady) {
        Write-Host "Docker läuft bereits."
        return
    }

    $dockerDesktop = Get-DockerDesktopPath
    if (-not $dockerDesktop) {
        throw "Docker Desktop wurde nicht gefunden. Bitte Docker Desktop installieren oder einmal manuell starten."
    }

    Write-Host "Starte Docker Desktop..."
    Start-Process -WindowStyle Hidden -FilePath $dockerDesktop

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerReady) {
            Write-Host "Docker ist bereit."
            return
        }
        Start-Sleep -Seconds 3
    }

    throw "Docker wurde innerhalb von $TimeoutSeconds Sekunden nicht bereit."
}

function Wait-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $async = $client.BeginConnect($HostName, $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1000, $false)) {
                $client.EndConnect($async)
                return
            }
        }
        catch {
        }
        finally {
            $client.Close()
        }
        Start-Sleep -Seconds 2
    }

    throw "Dienst auf $HostName`:$Port wurde innerhalb von $TimeoutSeconds Sekunden nicht erreichbar."
}

function Ensure-Venv {
    if (Test-Path ".\.venv\Scripts\python.exe") {
        return
    }

    Write-Step "Erstelle Python-Umgebung"
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        Invoke-Checked { python -m venv .venv } "Virtuelle Python-Umgebung konnte nicht erstellt werden."
        return
    }

    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        Invoke-Checked { py -3.12 -m venv .venv } "Virtuelle Python-Umgebung konnte nicht erstellt werden."
        return
    }

    throw "Benötigter Befehl nicht gefunden: python oder py. Installiere Python 3.11 oder 3.12."
}

function Ensure-Requirements {
    param([string]$ProjectPython)

    if ($SkipInstall) {
        return
    }

    $stamp = ".\.venv\.requirements-installed"
    $requirements = ".\requirements.txt"
    $needsInstall = -not (Test-Path $stamp)
    if ((Test-Path $stamp) -and (Test-Path $requirements)) {
        $needsInstall = (Get-Item $requirements).LastWriteTime -gt (Get-Item $stamp).LastWriteTime
    }

    if ($needsInstall) {
        Write-Step "Installiere Python-Abhängigkeiten"
        Invoke-Checked { & $ProjectPython -m pip install -r requirements.txt } "Python-Abhängigkeiten konnten nicht installiert werden."
        Set-Content -Path $stamp -Value (Get-Date).ToString("s")
    }
}

function Get-TripCount {
    try {
        $mongoEval = "const db=db.getSiblingDB('taxi_weather'); print(db.trips.countDocuments());"
        $output = docker compose exec -T mongo mongosh --quiet --eval $mongoEval 2>$null
        if ($LASTEXITCODE -ne 0) {
            return $null
        }
        return [int64]($output | Select-Object -Last 1)
    }
    catch {
        return $null
    }
}

function Import-DataIfNeeded {
    param([string]$ProjectPython)

    $tripCount = Get-TripCount
    if ($null -ne $tripCount) {
        Write-Host "MongoDB enthält aktuell $tripCount Fahrten."
    }

    $shouldImport = $ForceImport -or (($null -eq $tripCount -or $tripCount -eq 0) -and -not $SkipImportIfEmpty)
    if (-not $shouldImport) {
        return
    }

    Write-Step "Importiere Demo-Daten"
    foreach ($month in $Months) {
        Write-Host "Importiere $Year-$($month.ToString('00')) mit Limit $Limit..."
        Invoke-Checked { & $ProjectPython .\scripts\download_data.py --year $Year --month $month } "Daten-Download ist fehlgeschlagen."
        Invoke-Checked { & $ProjectPython .\scripts\import_data.py --year $Year --month $month --limit $Limit } "Datenimport ist fehlgeschlagen."
    }
}

function Stop-ExistingDashboard {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -like "python*" -or $_.Name -like "streamlit*") -and
        $_.CommandLine -like "*streamlit*run*app\dashboard.py*"
    }

    foreach ($process in $processes) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Wait-Http {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
        }
        Start-Sleep -Seconds 2
    }

    throw "Dashboard unter $Url wurde innerhalb von $TimeoutSeconds Sekunden nicht erreichbar."
}

Require-Command "docker"
Invoke-Checked { docker compose version | Out-Null } "Docker Compose ist nicht verfügbar."

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
}

Write-Step "Starte Docker"
Start-DockerDesktopIfNeeded

Write-Step "Starte MongoDB und Neo4j"
Invoke-Checked { docker compose up -d } "Docker-Container konnten nicht gestartet werden."
Wait-TcpPort "localhost" 27018
Wait-TcpPort "localhost" 7689
Wait-TcpPort "localhost" 7476

Ensure-Venv
$ProjectPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
Ensure-Requirements $ProjectPython
Import-DataIfNeeded $ProjectPython

Write-Step "Starte Streamlit-Dashboard"
Stop-ExistingDashboard
$dashboardUrl = "http://localhost:$DashboardPort"
$neo4jUrl = "http://localhost:7476"
$stdoutLog = Join-Path $ProjectRoot "streamlit.out.log"
$stderrLog = Join-Path $ProjectRoot "streamlit.err.log"
Start-Process -WindowStyle Hidden -FilePath $ProjectPython -ArgumentList @(
    "-m", "streamlit", "run", "app\dashboard.py",
    "--server.headless", "true",
    "--server.port", "$DashboardPort"
) -WorkingDirectory $ProjectRoot -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
Wait-Http $dashboardUrl

Write-Host ""
Write-Host "RainRoute NYC läuft." -ForegroundColor Green
Write-Host "Dashboard:      $dashboardUrl"
Write-Host "Neo4j Browser:  $neo4jUrl"
Write-Host "Neo4j Login:    neo4j / taxiweatherpass"

if (-not $NoBrowser) {
    Start-Process $dashboardUrl
    Start-Process $neo4jUrl
}
