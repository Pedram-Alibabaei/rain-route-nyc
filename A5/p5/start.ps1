param(
    [int]$Year = 2025,
    [int]$Month = 0,
    [int[]]$Months = @(1, 7, 12),
    [int]$Limit = 200000,
    [switch]$SkipInstall,
    [switch]$SkipImport
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Benötigter Befehl nicht gefunden: $Name"
    }
}

function Get-PythonBootstrap {
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        return ,@("python")
    }
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        return ,@("py", "-3.12")
    }
    throw "Benötigter Befehl nicht gefunden: python oder py. Installiere Python 3.11 oder 3.12."
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

function Wait-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds = 90
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

Require-Command "docker"

Invoke-Checked { docker compose version | Out-Null } "Docker Compose ist nicht verfügbar."
Invoke-Checked {
    docker info | Out-Null
} "Docker ist nicht erreichbar. Starte Docker Desktop und warte, bis Docker vollständig läuft."

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "Created .env from .env.example"
}

if (-not (Test-Path ".\.venv")) {
    $PythonBootstrap = Get-PythonBootstrap
    if ($PythonBootstrap.Count -eq 1) {
        & $PythonBootstrap[0] -m venv .venv
    }
    else {
        & $PythonBootstrap[0] $PythonBootstrap[1] -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Virtuelle Python-Umgebung konnte nicht erstellt werden."
    }
}

$ProjectPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $ProjectPython)) {
    throw "Python in .venv wurde nicht gefunden: $ProjectPython"
}

if (-not $SkipInstall) {
    Invoke-Checked { & $ProjectPython -m pip install --upgrade pip } "pip konnte nicht aktualisiert werden."
    Invoke-Checked { & $ProjectPython -m pip install -r requirements.txt } "Python-Abhängigkeiten konnten nicht installiert werden."
}

Invoke-Checked { docker compose up -d } "Docker-Container konnten nicht gestartet werden."

Write-Host "Warte auf MongoDB und Neo4j..."
Wait-TcpPort "localhost" 27018
Wait-TcpPort "localhost" 7689

if (-not $SkipImport) {
    if ($Month -gt 0) {
        $TargetMonths = @($Month)
    }
    else {
        $TargetMonths = $Months
    }

    foreach ($TargetMonth in $TargetMonths) {
        Write-Host ""
        Write-Host "Importiere $Year-$($TargetMonth.ToString('00')) mit Limit $Limit..."
        Invoke-Checked { & $ProjectPython .\scripts\download_data.py --year $Year --month $TargetMonth } "Daten-Download ist fehlgeschlagen."
        Invoke-Checked { & $ProjectPython .\scripts\import_data.py --year $Year --month $TargetMonth --limit $Limit } "Datenimport ist fehlgeschlagen."
    }
}

Write-Host ""
Write-Host "RainRoute NYC is ready."
Write-Host "Dashboard: http://localhost:8501"
Write-Host "Neo4j Browser: http://localhost:7476"
Write-Host ""
& $ProjectPython -m streamlit run .\app\dashboard.py
