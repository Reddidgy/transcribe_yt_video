#!/bin/bash

# Get the directory of this script to ensure relative paths work from anywhere
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "[*] Starting Public API from $SCRIPT_DIR..."
python3 "$SCRIPT_DIR/src/backend/public_api/public_transcribe_api.py"
