$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw '测试失败，停止打包' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --clean --distpath dist/v0.2.1 --workpath build/v0.2.1 VoiceInput.spec
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
Copy-Item README.md dist/v0.2.1/VoiceInput/README.md -Force
Copy-Item CHANGELOG.md dist/v0.2.1/VoiceInput/CHANGELOG.md -Force
Copy-Item pyproject.toml dist/v0.2.1/VoiceInput/pyproject.toml -Force
Copy-Item LICENSE dist/v0.2.1/VoiceInput/LICENSE -Force
Copy-Item THIRD_PARTY_NOTICES.md dist/v0.2.1/VoiceInput/THIRD_PARTY_NOTICES.md -Force
Copy-Item LICENSES dist/v0.2.1/VoiceInput/LICENSES -Recurse -Force
Copy-Item docs dist/v0.2.1/VoiceInput/docs -Recurse -Force
Compress-Archive -Path dist/v0.2.1/VoiceInput -DestinationPath dist/VoiceInput-V0.2.1-Windows-x64.zip -Force
