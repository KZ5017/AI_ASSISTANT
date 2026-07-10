param(
    [string]$Distro = 'Ubuntu-24.04',
    [string]$User = 'bober'
)

$ErrorActionPreference = 'Stop'
Write-Host '==> WSL listeners' -ForegroundColor Cyan
wsl -d $Distro -u $User bash -lc 'ss -ltnp | grep :8000 || true; ss -ltnp | grep :5173 || true'
Write-Host '==> Backend health' -ForegroundColor Cyan
try { Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health | Select-Object -ExpandProperty Content } catch { Write-Host $_.Exception.Message -ForegroundColor Yellow }
Write-Host '==> Frontend' -ForegroundColor Cyan
try { Invoke-WebRequest -UseBasicParsing http://localhost:5173 | Select-Object -ExpandProperty StatusCode } catch { Write-Host $_.Exception.Message -ForegroundColor Yellow }
