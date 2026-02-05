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

echo [*] Starting Backend Server...
cd ..\api
python transcribe_api.py
