$ErrorActionPreference = "Stop"

Write-Host "Building executable..."

pyinstaller --onefile --noconsole --name ICTestFixture src/ic_test_fixture/main.py

Write-Host "Build complete, appending checksum..."

python scripts\append_checksum.py dist\ICTestFixture.exe

Write-Host "Cleaning build artifacts..."

Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue
Remove-Item -Force ICTestFixture.spec -ErrorAction SilentlyContinue

Write-Host "Done"