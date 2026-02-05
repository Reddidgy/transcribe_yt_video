# Transcribe YT Video Service

A premium, full-stack application to transcribe YouTube videos and generate AI-ready prompts for summaries and insights.

## Features
- **Effortless Transcription**: Convert any YouTube video to text in seconds using OpenAI Whisper AI.
- **AI-Ready Prompts**: Automatically concatenates transcripts with a world-class translation prompt.
- **Premium UI**: Dark-themed, high-performance interface with silky-smooth animations.
- **Robust Configuration**: Environment-based portability for dev, staging, and production.
- **Automated Versioning**: Git-hook powered version increments (currently v0.0.1).
- **Comprehensive Logging**: Tracks API activity and unique visitor metrics.

## Tech Stack
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide React.
- **Backend**: Python, Flask, Flask-CORS, `pytubefix`, `openai-whisper`.

## Project Structure
- `src/backend/api`: Flask server and logging logic.
- `src/backend/transcribe_service`: Core transcription scripts and prompts.
- `src/frontend`: React application source code.
- `scripts`: Utility scripts for versioning and execution.

---

## How to Build and Run

### Prerequisites
- Node.js (v18+) and npm.
- Python 3.9+.
- Git.

### Environment Configuration
1. **Frontend**: Create `src/frontend/.env` (see `src/frontend/.env.example`).
   ```text
   VITE_API_URL=http://localhost:5000
   ```
2. **Backend**: Create `.env` in the root (see `.env.example`) to configure `PORT` and `HOST`.

### Development Mode
1. **Start Backend**:
   ```powershell
   cd src/backend/api
   python transcribe_api.py
   ```
2. **Start Frontend**:
   ```powershell
   cd src/frontend
   npm install
   npm run dev
   ```

### Production Build and Run
We provide scripts for one-click production setup:

**Windows (CMD)**:
```cmd
.\scripts\build_and_run.bat
```

**Linux/Mac (Bash)**:
```bash
bash ./scripts/build_and_run.sh
```

These scripts will automatically build the frontend production assets and launch the backend server.

---

## Troubleshooting (Remote Linux / Ubuntu)
- If transcription fails, ensure **FFmpeg** is installed on your system.
    - **Ubuntu 20.04**: `sudo apt update && sudo apt install ffmpeg`
    - **Windows**: `winget install ffmpeg`
- If you see memory errors, ensure the server has at least 2GB of RAM to load the Whisper `base` model.
- The script handles `pytubefix` and `whisper` installations automatically if permissions allow.

## Automated Versioning
The project uses an automated versioning system. Every time you commit, a Git pre-commit hook runs `scripts/bump_version.py` to increment the patch version. 

To manually update major/minor versions, edit the `version` file at the root.

---

## Author
Built by @Reddidgy (2026)
