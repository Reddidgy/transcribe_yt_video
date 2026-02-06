@echo off
REM Production Build and Run Script (Batch)
REM This script builds the frontend and starts the backend server.

echo [*] Building Frontend...
cd src\frontend
call npm install
call npm run build

echo [*] Setting up Backend...
cd ..\backend\transcribe_service
python -m pip install -r requirements.txt

echo [*] Starting Public API Server...
cd ..\public_api
python public_transcribe_api.py
