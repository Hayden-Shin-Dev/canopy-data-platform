$ErrorActionPreference = "Stop"

python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name CanopyDemo `
  --distpath "$PSScriptRoot\..\dist" `
  --workpath "$PSScriptRoot\..\build\CanopyDemo" `
  "$PSScriptRoot\launch_canopy_demo.py"

Write-Host "Created $PSScriptRoot\..\dist\CanopyDemo.exe"
Write-Host "Keep CanopyDemo.exe in the repository root next to the scripts, assets, data, and models folders."
