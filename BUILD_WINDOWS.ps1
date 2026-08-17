$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ first."
}

Write-Host "Installing pinned build dependencies..." -ForegroundColor Cyan
py -m pip install --upgrade pip
py -m pip install -r ".\requirements-build.txt"

Write-Host "Running Python security scan..." -ForegroundColor Cyan
py -m bandit -q -r ".\app" -x ".\app\__pycache__"

Write-Host "Building application..." -ForegroundColor Cyan
py -m PyInstaller --noconfirm --clean ".\CoXRaidDashboard.spec"

if (-not (Test-Path ".\dist\CoXRaidDashboard.exe")) {
    throw "Build did not produce dist\CoXRaidDashboard.exe"
}

$InnoCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)
$Inno = $InnoCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($Inno) {
    Write-Host "Building installer..." -ForegroundColor Cyan
    & $Inno ".\installer\CoXRaidDashboard.iss"
    Write-Host "Installer: .\dist-installer\CoXRaidDashboard-Setup.exe" -ForegroundColor Green
} else {
    Write-Host "Executable built: .\dist\CoXRaidDashboard.exe" -ForegroundColor Green
    Write-Host "Inno Setup 6 not found; install it to build Setup.exe." -ForegroundColor Yellow
}

if (Test-Path ".\dist-installer\CoXRaidDashboard-Setup.exe") {
    $Hash = Get-FileHash ".\dist-installer\CoXRaidDashboard-Setup.exe" -Algorithm SHA256
    "$($Hash.Hash.ToLower())  CoXRaidDashboard-Setup.exe" | Set-Content ".\dist-installer\SHA256SUMS.txt"
    Write-Host "SHA256SUMS.txt created." -ForegroundColor Green
}
