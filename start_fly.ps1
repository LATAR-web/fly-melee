<#
.SYNOPSIS
    Lanzador de Fly-Melee para Windows (PowerShell).
    Simulación biofísica del conectoma de Drosophila (400k neuronas) en Super Smash Bros. Melee.

.DESCRIPTION
    Inicia la simulación neuronal de la mosca, el servidor de telemetría web 3D y Dolphin.
    Equivalente para Windows de start_fly.sh.

.PARAMETER Mode
    Modo de ejecución:
    1: Humano vs Mosca Luigi
    2: Mosca Luigi vs Bot CPU 9
    3: Humano vs Mosca Fox (20XX)
    4 o --web: Solo panel web 3D
    5 o --lightweight: Modo ultra-fluido (49k neuronas)
#>
param(
    [Parameter(Position=0)]
    [string]$Mode = "",
    [switch]$Web,
    [switch]$Lightweight,
    [string]$Iso = "",
    [string]$Character = "",
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$Dir = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Dir)) {
    $Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($Dir)) {
    $Dir = (Get-Location).Path
}

# 1. Detectar entorno virtual de Python en Windows
$Python = $null
$Candidates = @(
    (Join-Path $Dir ".venv\Scripts\python.exe"),
    (Join-Path $Dir "venv\Scripts\python.exe")
)

if ($env:VIRTUAL_ENV) {
    $Candidates += (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe")
}

foreach ($c in $Candidates) {
    if (Test-Path $c) {
        $Python = $c
        break
    }
}

if (-not $Python) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $Python = $pyCmd.Source
    } else {
        $pyCmd2 = Get-Command py -ErrorAction SilentlyContinue
        if ($pyCmd2) {
            $Python = $pyCmd2.Source
        }
    }
}

if (-not $Python) {
    Write-Host "❌ Error: No se encontró Python 3 instalado." -ForegroundColor Red
    Write-Host "   Instálalo desde python.org y configura el entorno virtual con:" -ForegroundColor Yellow
    Write-Host "     python -m venv .venv" -ForegroundColor Cyan
    Write-Host "     .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "     pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

$DefaultIso = Join-Path $Dir "data\games\ssbm.iso"
$Port = 8085
$Url = "http://localhost:$Port"

function Test-DashboardRunning {
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue
        foreach ($p in $procs) {
            if ($p.CommandLine -like "*dashboard_server.py*") {
                return $true
            }
        }
    } catch {}
    return $false
}

function Start-DashboardServer {
    if (-not (Test-DashboardRunning)) {
        Write-Host "🌐 Iniciando servidor web de telemetría ($Url)..." -ForegroundColor Cyan
        $scriptPath = Join-Path $Dir "dashboard_server.py"
        Start-Process -FilePath $Python -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden
        Start-Sleep -Seconds 1
    }
}

function Open-Browser {
    try {
        Start-Process $Url
    } catch {
        Write-Host "ℹ️ Abre manualmente en tu navegador: $Url" -ForegroundColor Yellow
    }
}

# Manejar modo solo web
if ($Web -or $Mode -eq "--web" -or $Mode -eq "4") {
    Write-Host "🌐 Iniciando solo panel web en $Url ..." -ForegroundColor Cyan
    Start-DashboardServer
    Open-Browser
    Write-Host "✅ Panel web activo en: $Url" -ForegroundColor Green
    exit 0
}

$Choice = $Mode
if ($Mode -eq "5" -or $Lightweight -or $Mode -eq "--lightweight" -or $Mode -eq "-l") {
    $Choice = "5"
}

if ([string]::IsNullOrWhiteSpace($Choice)) {
    Write-Host "=================================================================" -ForegroundColor DarkCyan
    Write-Host "  🪰 CEREBRO DE LA MOSCA (Drosophila) × SUPER SMASH BROS MELEE" -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor DarkCyan
    Write-Host "¿Cómo quieres jugar?" -ForegroundColor White
    Write-Host "  1) 🎮 Jugar tú contra la Mosca (P1: Luigi, P2: Tú con Teclado/Mando) [ENTER]" -ForegroundColor Yellow
    Write-Host "  2) 🤖 Ver a la Mosca humillar a un Bot CPU Nivel 9 en Dolphin"
    Write-Host "  3) 🦊 Jugar tú contra la Mosca Fox McCloud (20XX Shine)"
    Write-Host "  4) 🌐 Solo abrir el Panel Web 3D interactivo (Sin emulador)"
    Write-Host "  5) ⚡ Modo Ultra-Fluido 60 FPS (49k neuronas / 0 lag / 2ms por frame)"
    Write-Host "=================================================================" -ForegroundColor DarkCyan

    $timeoutSeconds = 5
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host "Opción [1-5] (Inicia juego 1 automáticamente en 5s): " -NoNewline -ForegroundColor Yellow

    try {
        while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -eq [ConsoleKey]::Enter) {
                    break
                } else {
                    $userInput = $key.KeyChar.ToString()
                    Write-Host $userInput
                    break
                }
            }
            Start-Sleep -Milliseconds 100
        }
    } catch {
        # En entornos no interactivos o con entrada redirigida
        $userInput = ""
    }

    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $Choice = "1"
        Write-Host "1 (por defecto)" -ForegroundColor Green
    } else {
        $Choice = $userInput
    }
    Write-Host ""
}

$FlyChar = "luigi"
$ExtraArgsList = @()

if ($Lightweight -or ($ExtraArgs -contains "--lightweight") -or ($ExtraArgs -contains "-l")) {
    $ExtraArgsList += "--lightweight"
}

switch ($Choice) {
    "2" {
        Write-Host "🤖 Modo Espectador: Mosca Luigi vs Bot CPU Nivel 9..." -ForegroundColor Cyan
        $FlyChar = "luigi"
        $ExtraArgsList += @("--cpu", "9")
    }
    "3" {
        Write-Host "🦊 Modo Desafío 20XX: Jugador Humano vs Mosca Fox..." -ForegroundColor Yellow
        $FlyChar = "fox"
    }
    "4" {
        Write-Host "🌐 Abriendo solo visualizador web en $Url ..." -ForegroundColor Cyan
        Start-DashboardServer
        Open-Browser
        Write-Host "✅ Panel web activo en: $Url" -ForegroundColor Green
        exit 0
    }
    "5" {
        Write-Host "⚡ Modo Ultra-Fluido 60 FPS: Mosca Luigi (49k neuronas, 0 lag)..." -ForegroundColor Green
        $FlyChar = "luigi"
        if (-not ($ExtraArgsList -contains "--lightweight")) {
            $ExtraArgsList += "--lightweight"
        }
    }
    default {
        Write-Host "🎮 Modo Combate: Jugador Humano vs Mosca Luigi..." -ForegroundColor Green
        $FlyChar = "luigi"
    }
}

if (-not [string]::IsNullOrWhiteSpace($Character)) {
    $FlyChar = $Character
}

# 1. Verificar y asegurar la existencia de la ISO de Melee
$FastDownloadScript = Join-Path $Dir "fast_download.py"
& $Python $FastDownloadScript

# 2. Iniciar servidor de telemetría web en segundo plano
Start-DashboardServer

# 3. Abrir navegador
Write-Host "🌐 Abriendo visualizador web en el navegador..." -ForegroundColor Cyan
Open-Browser

# 4. Lanzar emulador Dolphin con el juego Melee y la Mosca
Write-Host "🚀 Abriendo emulador Dolphin con Super Smash Bros. Melee..." -ForegroundColor Green

$IsoToUse = if (-not [string]::IsNullOrWhiteSpace($Iso)) { $Iso } elseif (Test-Path $DefaultIso) { $DefaultIso } else { "" }

while ($true) {
    $cmdArgs = @((Join-Path $Dir "fly_melee.py"))
    if ($IsoToUse -and (Test-Path $IsoToUse)) {
        $cmdArgs += @("--iso", $IsoToUse)
    }
    $cmdArgs += @("--character", $FlyChar)
    if ($ExtraArgsList.Count -gt 0) {
        $cmdArgs += $ExtraArgsList
    }
    if ($ExtraArgs) {
        $cmdArgs += $ExtraArgs
    }

    & $Python $cmdArgs

    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor DarkGray
    Write-Host "🎮 Sesión de juego finalizada." -ForegroundColor Cyan
    Write-Host "Presiona ENTER para reiniciar la Mosca o escribe 'q' + ENTER para salir:" -ForegroundColor Yellow
    Write-Host "=================================================================" -ForegroundColor DarkGray
    $restart = Read-Host
    if ($restart -match "^[qQ]$") {
        break
    }
}
