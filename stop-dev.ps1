# Stops the Wiseweb-AI dev stack: backend API (:8000), demo site (:8001), Vite frontend (:5173).
$Ports = 8000, 8001, 5173

$Procs = Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

if (-not $Procs) {
    Write-Host "Nothing is running on ports $($Ports -join ', ') - dev stack already stopped." -ForegroundColor Green
    exit 0
}

foreach ($Id in $Procs) {
    $P = Get-Process -Id $Id -ErrorAction SilentlyContinue
    if ($P) {
        Stop-Process -Id $Id -Force
        Write-Host "[$($P.Id)] stopped $($P.ProcessName)" -ForegroundColor Yellow
    }
}

Start-Sleep -Milliseconds 500
$Leftover = Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue
if ($Leftover) {
    Write-Host "WARNING: some services still listening: $((Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue | Select-Object -Unique LocalPort) -join ', ')" -ForegroundColor Red
}
else {
    Write-Host "Wiseweb-AI dev stack stopped." -ForegroundColor Green
}