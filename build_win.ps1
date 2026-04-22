Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

python -m PyInstaller --clean -y vertexmarkdown.spec
python .\scripts\smoke_test_win_bundle.py
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer_win.iss

