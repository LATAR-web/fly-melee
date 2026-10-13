<#
.SYNOPSIS
    Diagnóstico y Reparación de Mandos y Dispositivos Bluetooth en Windows.
    Equivalente para Windows de fix_bluetooth_gamepad.sh.
#>
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
$Python = "python"
$candidates = @(
    (Join-Path $Dir ".venv\Scripts\python.exe"),
    (Join-Path $Dir "venv\Scripts\python.exe")
)
foreach ($c in $candidates) {
    if (Test-Path $c) {
        $Python = $c
        break
    }
}

Write-Host "==================================================================" -ForegroundColor DarkCyan
Write-Host "  🔧 DIAGNÓSTICO Y REPARACIÓN DE MANDOS / BLUETOOTH EN WINDOWS" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor DarkCyan

Write-Host "1. Abriendo panel nativo de Dispositivos de Juego de Windows (joy.cpl)..." -ForegroundColor Cyan
Start-Process joy.cpl

Write-Host "2. Abriendo Configuración de Bluetooth y Dispositivos de Windows..." -ForegroundColor Cyan
try {
    Start-Process "ms-settings:bluetooth"
} catch {
    Write-Host "   (No se pudo abrir la configuración moderna de Bluetooth directamente)" -ForegroundColor Gray
}

Write-Host "`n3. Comprobando servicio de compatibilidad Bluetooth de Windows (bthserv)..." -ForegroundColor Cyan
try {
    $svc = Get-Service -Name "bthserv" -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "   Estado del servicio Bluetooth: $($svc.Status)" -ForegroundColor Yellow
        $resp = Read-Host "¿Deseas reiniciar el servicio Bluetooth de Windows ahora? [s/N]"
        if ($resp -match "^[sSyY]$") {
            try {
                Restart-Service -Name "bthserv" -Force -ErrorAction Stop
                Write-Host "   ✅ Servicio Bluetooth reiniciado con éxito." -ForegroundColor Green
            } catch {
                Write-Host "   ⚠️ Se requieren permisos de Administrador para reiniciar el servicio Bluetooth." -ForegroundColor Yellow
                Write-Host "      (Abre PowerShell como Administrador si necesitas reiniciar el servicio)." -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "   ℹ️ Servicio bthserv no encontrado (¿este equipo tiene adaptador Bluetooth?)." -ForegroundColor Gray
    }
} catch {
    Write-Host "   ℹ️ No se pudo consultar el servicio Bluetooth." -ForegroundColor Gray
}

Write-Host "`n4. Ejecutando detector e integrador de mandos para Dolphin (detect_controller.py)..." -ForegroundColor Cyan
& $Python (Join-Path $Dir "detect_controller.py")

Write-Host "`n==================================================================" -ForegroundColor DarkCyan
Write-Host "👉 Si tu mando está conectado pero no responde:" -ForegroundColor Yellow
Write-Host "   1) Mantén presionado el botón HOME/MODE durante 5 a 10 segundos para"
Write-Host "      cambiar entre el modo DirectInput y el modo XInput."
Write-Host "   2) Verifica que aparezca en la ventana de joy.cpl."
Write-Host "   3) Conéctalo mediante cable USB si el adaptador Bluetooth tiene interferencias."
Write-Host "==================================================================" -ForegroundColor DarkCyan
