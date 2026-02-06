@echo off
REM Get the directory of this script to ensure relative paths work from anywhere
set SCRIPT_DIR=%~dp0
echo [*] Starting Hard API (Transcription Engine) from %SCRIPT_DIR%...
python "%SCRIPT_DIR%src\backend\hard_api\transcribe_api.py"
pause
