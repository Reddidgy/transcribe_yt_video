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
- `src/backend/public_api`: Public-facing Flask server for general requests and transcription proxying.
- `src/backend/hard_api`: Transcription engine (Whisper) that handles the heavy lifting.
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
   VITE_API_URL=http://localhost:4520
   ```
2. **Backend**: Create `.env` in the root (see `.env.example`).
   ```text
   PORT=4520
   HOST=0.0.0.0
   HARD_API_HOST=http://<hard_api_machine_ip>:4520
   ```

### Running the Services

This application uses a dual-API architecture. You can start the appropriate API on each machine from the project root using the provided scripts.

**Note**: These scripts are location-independent and can be run from anywhere.

1. **Start Hard API (Transcription Machine)**:
   - **Windows**: Run `run_hard_api.bat`
   - **Linux**: Run `bash scripts/run_hard_api.sh` (if you create one) or `python3 src/backend/hard_api/transcribe_api.py`

2. **Start Public API & Frontend (Public-Facing Machine)**:
   - **Backend**:
     - **Windows**: `python src/backend/public_api/public_transcribe_api.py`
     - **Linux**: Run `./run_public_api.sh`
   - **Frontend**:
     ```powershell
     cd src/frontend
     npm run dev
     ```

---

## Troubleshooting (Remote Linux / Ubuntu)
- If transcription fails, ensure **FFmpeg** is installed on your system.
    - **Ubuntu 20.04**: `sudo apt update && sudo apt install ffmpeg`
    - **Windows**: `winget install ffmpeg`
- If you see memory errors, ensure the transcription server has at least 2GB of RAM to load the Whisper `base` model.
- The script handles `pytubefix` and `whisper` installations automatically if permissions allow.
- **Proxy Timeouts**: If serving via Nginx or similar, you might encounter 504 Gateway Timeouts for long videos. As of v0.0.1+ (Async Update), the application handles this by processing transcription in the background and polling for results from the frontend. No special Nginx configuration is required, but ensure `client_max_body_size` and other standard limits are appropriate.

## Automated Versioning
The project uses an automated versioning system. Every time you commit, a Git pre-commit hook runs `scripts/bump_version.py` to increment the patch version. 

To manually update major/minor versions, edit the `version` file at the root.

---

## Deployment (Remote Server)

### Sub-path Serving
This application is configured to be served from the `/transcribe_youtube/` sub-path (e.g., `https://domain.com/transcribe_youtube/`).

If you need to change this:
1.  **Frontend**: Update the `base` property in `src/frontend/vite.config.ts`.
2.  **Nginx**: Ensure your Nginx `alias` and `rewrite` rules match the new path.

### Example Nginx Config:
```nginx
location /transcribe_youtube/ {
    alias /path/to/project/src/frontend/dist/;
    rewrite ^/transcribe_youtube/app$ /transcribe_youtube/index.html last;
    try_files $uri $uri/ =404;
}
```

---

## Author
Built by @Reddidgy (2026)
