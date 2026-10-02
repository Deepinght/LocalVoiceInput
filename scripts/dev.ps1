param([switch]$Preview)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!(Test-Path '.venv/Scripts/python.exe')) { py -3 -m venv .venv }
& .venv/Scripts/python.exe -m ensurepip --upgrade
& .venv/Scripts/python.exe -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
if ($Preview) { & .venv/Scripts/python.exe -m voiceinput --preview '氮气流量一百标方每小时温度五百度' }
else { & .venv/Scripts/python.exe -m voiceinput }
