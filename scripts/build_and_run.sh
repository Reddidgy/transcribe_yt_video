#!/bin/bash

# Production Build and Run Script (Bash)
# This script builds the frontend and starts the backend server.

echo "[*] Building Frontend..."
cd src/frontend
npm install
npm run build

echo "[*] Setting up Backend..."
cd ../backend/transcribe_service
python -m pip install -r requirements.txt

echo "[*] Starting Backend Server..."
cd ../api
python app.py
