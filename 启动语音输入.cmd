@echo off
cd /d "%~dp0"
if exist "dist\v0.2.1\VoiceInput\VoiceInput.exe" (
  start "" "dist\v0.2.1\VoiceInput\VoiceInput.exe"
) else (
  echo Release not found. Please run scripts\package.ps1 first.
  pause
)
