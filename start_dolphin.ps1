<#
.SYNOPSIS
    Menú integral de Dolphin y herramientas de Fly-Melee para Windows (PowerShell).
    Equivalente para Windows de start_dolphin.sh.
#>
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

# Detectar Python
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
        Write-Host "❌ Error: No se encontró Python 3 instalado." -ForegroundColor Red
        exit 1
    }
}

$DefaultIso = Join-Path $Dir "data\games\ssbm.iso"
$Url = "http://localhost:8085"

function Start-DashboardIfNeeded {
    $procs = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue
    $running = $false
    foreach ($p in $procs) {
        if ($p.CommandLine -like "*dashboard_server.py*") {
            $running = $true
            break
        }
    }
    if (-not $running) {
        Write-Host "Iniciando visualizador 3D en segundo plano..." -ForegroundColor Cyan
        Start-Process -FilePath $Python -ArgumentList "`"$(Join-Path $Dir 'dashboard_server.py')`"" -WindowStyle Hidden
        Start-Sleep -Seconds 1
    }
    try { Start-Process $Url } catch {}
}

Write-Host "=================================================================" -ForegroundColor DarkCyan
Write-Host "  🪰 CEREBRO DE LA MOSCA (Drosophila 400k) × DOLPHIN / MELEE" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor DarkCyan
Write-Host "Selecciona una opción:" -ForegroundColor White
Write-Host "  1) Iniciar Dolphin: Mosca vs Humano (Tú en P2)" -ForegroundColor Yellow
Write-Host "  2) Iniciar Dolphin: Mosca vs Bot CPU Nivel 9 (P2 automático)"
Write-Host "  3) Entrenamiento Neural vs Bots CPU Nivel 9 (50 / 100 partidas)"
Write-Host "  4) Detectar y Configurar Mando / Gamepad (USB o Bluetooth)"
Write-Host "  5) Diagnóstico y Reparación de Mandos en Windows"
Write-Host "  6) Ejecutar Test de Simulación Neural en Terminal"
Write-Host "  7) Descargar ISO de Melee de Alta Velocidad (fast_download.py)"
Write-Host "  8) Salir"
Write-Host "=================================================================" -ForegroundColor DarkCyan
$Opt = Read-Host "Opción [1-8]"

switch ($Opt) {
    "1" {
        Write-Host "Iniciando conexión con Dolphin contra Jugador Humano..." -ForegroundColor Green
        Start-DashboardIfNeeded

        Write-Host "Selecciona personaje de la Mosca:"
        Write-Host "  1) 🟢 Luigi (Wavedash SSS & Shoryuken Kill Confirms) [Recomendado]"
        Write-Host "  2) 🦊 Fox McCloud (20XX Shine & Spacie)"
        $CharOpt = Read-Host "Personaje [1-2] (1)"
        $FlyChar = if ($CharOpt -eq "2") { "fox" } else { "luigi" }

        $IsoPath = ""
        if (Test-Path $DefaultIso) {
            Write-Host "📁 Usando ISO verificada: $DefaultIso" -ForegroundColor Cyan
            $IsoPath = $DefaultIso
        } else {
            $IsoPath = Read-Host "Ruta a la ISO de Melee (deja en blanco si ya está corriendo en Dolphin)"
            if ($IsoPath) { $IsoPath = $IsoPath.Trim('"', "'").Trim() }
        }

        $cmdArgs = @((Join-Path $Dir "fly_melee.py"), "--character", $FlyChar)
        if (-not [string]::IsNullOrWhiteSpace($IsoPath) -and (Test-Path $IsoPath)) {
            $cmdArgs += @("--iso", $IsoPath)
        }
        & $Python $cmdArgs
    }
    "2" {
        Write-Host "Iniciando conexión con Dolphin contra Bot CPU Nivel 9..." -ForegroundColor Green
        Start-DashboardIfNeeded

        Write-Host "Selecciona personaje de la Mosca:"
        Write-Host "  1) 🟢 Luigi (Wavedash SSS & Shoryuken Kill Confirms) [Recomendado]"
        Write-Host "  2) 🦊 Fox McCloud (20XX Shine & Spacie)"
        $CharOpt = Read-Host "Personaje [1-2] (1)"
        $FlyChar = if ($CharOpt -eq "2") { "fox" } else { "luigi" }

        $IsoPath = ""
        if (Test-Path $DefaultIso) {
            Write-Host "📁 Usando ISO verificada: $DefaultIso" -ForegroundColor Cyan
            $IsoPath = $DefaultIso
        } else {
            $IsoPath = Read-Host "Ruta a la ISO de Melee"
            if ($IsoPath) { $IsoPath = $IsoPath.Trim('"', "'").Trim() }
        }

        $cmdArgs = @((Join-Path $Dir "fly_melee.py"), "--cpu", "9", "--character", $FlyChar)
        if (-not [string]::IsNullOrWhiteSpace($IsoPath) -and (Test-Path $IsoPath)) {
            $cmdArgs += @("--iso", $IsoPath)
        }
        & $Python $cmdArgs
    }
    "3" {
        Write-Host "=================================================================" -ForegroundColor DarkCyan
        Write-Host "  🧬 ENTRENAMIENTO BIOLÓGICO ACELERADO VS BOTS CPU NIVEL 9" -ForegroundColor Green
        Write-Host "=================================================================" -ForegroundColor DarkCyan
        Write-Host "Selecciona el personaje de la Mosca a entrenar:"
        Write-Host "  1) 🟢 Luigi (Wavedash SSS & Shoryuken) [Recomendado]"
        Write-Host "  2) 🦊 Fox (20XX SSS)"
        $CharOpt = Read-Host "Personaje [1-2] (1)"
        $FlyChar = if ($CharOpt -eq "2") { "fox" } else { "luigi" }

        Write-Host "Selecciona la cantidad de partidas:"
        Write-Host "  1) 50 Partidas (Rápido, ~1.5 seg)"
        Write-Host "  2) 100 Partidas (Profundo con adaptación multi-personaje, ~3 seg)"
        Write-Host "  3) Cantidad personalizada"
        $MatchOpt = Read-Host "Opción [1-3] (por defecto 50)"
        $NumMatches = 50
        switch ($MatchOpt) {
            "2" { $NumMatches = 100 }
            "3" {
                $custom = Read-Host "Introduce el número de partidas"
                if ($custom -match "^\d+$") { $NumMatches = [int]$custom }
            }
            default { $NumMatches = 50 }
        }
        Write-Host "Ejecutando: python train_fly.py $NumMatches --cpu 9 --character $FlyChar" -ForegroundColor Cyan
        & $Python (Join-Path $Dir "train_fly.py") $NumMatches --cpu 9 --character $FlyChar
    }
    "4" {
        Write-Host "Iniciando detector y configurador de mandos..." -ForegroundColor Cyan
        & $Python (Join-Path $Dir "detect_controller.py")
    }
    "5" {
        $fixScript = Join-Path $Dir "fix_bluetooth_gamepad.ps1"
        if (Test-Path $fixScript) {
            & $fixScript
        } else {
            Start-Process joy.cpl
            try { Start-Process "ms-settings:bluetooth" } catch {}
        }
    }
    "6" {
        Write-Host "Ejecutando simulación biológica en tiempo real..." -ForegroundColor Cyan
        & $Python (Join-Path $Dir "test_fly_brain.py")
    }
    "7" {
        Write-Host "Iniciando descarga multihilo de la ISO de Melee..." -ForegroundColor Cyan
        & $Python (Join-Path $Dir "fast_download.py")
    }
    "8" {
        exit 0
    }
    default {
        Write-Host "Opción no válida." -ForegroundColor Red
    }
}
