import os
import sys
import re
import subprocess
import json
import time
import logging
from logging.handlers import RotatingFileHandler

# Setup Logging
def setup_logger():
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "transcribe.log")

    logger = logging.getLogger("transcribe_service")
    logger.setLevel(logging.INFO)

    # Format: Timestamp [LEVEL] - Message
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Rotating: 1MB per file, max 5 files)
    file_handler = RotatingFileHandler(log_file, maxBytes=1*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

# Self-Healing: Ensure dependencies are installed
_DEPS_PROCESSED = set()

def get_site_packages_path():
    try:
        import site
        # Get usersitepackages or site-packages
        paths = site.getsitepackages() if hasattr(site, 'getsitepackages') else []
        if hasattr(site, 'getusersitepackages'):
            paths.append(site.getusersitepackages())
        return paths
    except:
        return []

def ensure_dependencies(dep_name=None, force_upgrade=False):
    global _DEPS_PROCESSED
    deps = [dep_name] if dep_name else ["youtube-transcript-api", "yt-dlp"]

    for dep in deps:
        if dep in _DEPS_PROCESSED and not force_upgrade:
            continue

        module_name = dep.replace("-", "_")
        try:
            if force_upgrade: raise ImportError("Forced upgrade requested")
            __import__(module_name)
        except ImportError:
            logger.info(f"Dependency '{dep}' missing or upgrade requested. Attempting AGGRESSIVE install...")
            try:
                # Use --force-reinstall and --no-cache-dir to bypass environment locks
                # Pin youtube-transcript-api to a known-good version to avoid name-collision / broken wheels
                dep_to_install = dep
                if dep == "youtube-transcript-api":
                    dep_to_install = "youtube-transcript-api==0.6.2"
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-cache-dir", dep_to_install]
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"Successfully processed '{dep}'.")

                # Refresh path
                for path in get_site_packages_path():
                    if path not in sys.path:
                        sys.path.insert(0, path)

                _DEPS_PROCESSED.add(dep)
            except Exception as e:
                logger.error(f"Failed to process '{dep}'. Please install manually: {sys.executable} -m pip install {dep}")
                logger.debug(f"Install error: {str(e)}")

        # Post-check: make sure we actually got the expected library (some environments install a conflicting package)
        if dep == "youtube-transcript-api":
            try:
                from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
                has_expected_api = hasattr(YouTubeTranscriptApi, "get_transcript") or hasattr(YouTubeTranscriptApi, "list_transcripts")
                if not has_expected_api:
                    logger.warning(
                        "Detected unexpected 'youtube_transcript_api' package (missing expected APIs). "
                        "Forcing reinstall of a known-good version..."
                    )
                    cmd = [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "--force-reinstall",
                        "--no-cache-dir",
                        "youtube-transcript-api==0.6.2",
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    nuclear_reload(["youtube_transcript_api"])
                    _DEPS_PROCESSED.add(dep)
            except Exception as e:
                logger.warning(f"Post-check for youtube-transcript-api failed: {str(e)}")

def nuclear_reload(module_names):
    """Deep reload by clearing sys.modules first."""
    for name in list(sys.modules.keys()):
        for target in module_names:
            if name == target or name.startswith(target + "."):
                del sys.modules[name]

ensure_dependencies()

def extract_video_id(url):
    logger.info(f"Extracting video ID from URL: {url}")
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            vid = match.group(1)
            logger.info(f"Successfully extracted video ID: {vid}")
            return vid
    logger.warning(f"Failed to extract video ID from URL: {url}")
    return None

# Stealth Headers
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
REFERER = "https://www.youtube.com/"

def fetch_via_ytdlp(url, video_id):
    """Strategy C: yt-dlp fallback with Stealth & Path Tracking."""
    logger.info(f"Attempting Strategy C: yt-dlp fallback for URL: {url}")
    env = os.environ.copy()

    def run_ytdlp():
        prefix = f"sub_{video_id}_{int(time.time())}"
        # STEALTH: User-Agent and Referer
        base_cmds = [
            [sys.executable, "-m", "yt_dlp"],
            ["yt-dlp"]
        ]
        args = [
            "--write-sub", "--write-auto-sub", "--skip-download",
            "--sub-langs", "en,ru", "--no-check-certificate", "--geo-bypass",
            "--ignore-errors", "--user-agent", USER_AGENT,
            "--add-header", f"Referer:{REFERER}",
            "-o", prefix, url
        ]

        for base in base_cmds:
            try:
                cmd = base + args
                logger.debug(f"Trying command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env, timeout=90)
                if result.returncode == 0:
                    return result, prefix
            except: continue

        return subprocess.run(["yt-dlp"] + args, capture_output=True, text=True, encoding='utf-8', env=env, timeout=90), prefix

    result, prefix = run_ytdlp()

    if result.returncode != 0 and "yt-dlp" not in _DEPS_PROCESSED:
        logger.warning(f"yt-dlp failed (code {result.returncode}). Attempting AGGRESSIVE pip update...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-cache-dir", "yt-dlp"], capture_output=True, env=env)
            result, prefix = run_ytdlp()
        except: pass

    # SURGICAL DISCOVERY: Parse stdout for the actual filename
    downloaded_file = None
    if result.stdout:
        # Look for the "Writing video subtitles to: <file>" line
        match = re.search(r'\[info\] Writing video subtitles to: (.*\.vtt|.*\.srt)', result.stdout)
        if match:
            downloaded_file = match.group(1).strip()
            logger.info(f"Surgically identified downloaded file: {downloaded_file}")

    try:
        # Search dirs for the file if surgical discovery failed
        search_dirs = [".", os.path.dirname(os.path.abspath(__file__))]
        candidate_files = [downloaded_file] if downloaded_file else []

        if not downloaded_file:
            for d in search_dirs:
                if not os.path.exists(d): continue
                candidate_files.extend([os.path.join(d, f) for f in os.listdir(d) if f.startswith(prefix) and (f.endswith(".vtt") or f.endswith(".srt"))])

        for file_path in candidate_files:
            if not file_path or not os.path.exists(file_path): continue

            logger.info(f"Processing subtitle file: {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8", errors='ignore') as file:
                    content = file.read()

                # Cleanup VTT / SRT
                text = re.sub(r'WEBVTT|KIND|LANGUAGE|FILE|NOTE.*', '', content, flags=re.I)
                text = re.sub(r'\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}.*?\n', '', text)
                text = re.sub(r'<[^>]+>', '', text)
                text = " ".join([l.strip() for l in text.splitlines() if l.strip()])

                os.remove(file_path)
                if text and len(text) > 20: # Sanity check: must be longer than just title
                    logger.info("Strategy C SUCCESS!")
                    return text
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {str(e)}")

        # FINAL DIAGNOSTIC: If all failed, log a sub list check
        if result.returncode == 0:
            logger.warning("Strategy C: Code 0 but no usable subtitle content found. Checking available subs...")
            diag_cmd = [sys.executable, "-m", "yt_dlp", "--list-subs", "--user-agent", USER_AGENT, url]
            diag_res = subprocess.run(diag_cmd, capture_output=True, text=True, encoding='utf-8', env=env)
            if diag_res.stdout: logger.info(f"Available subtitles from server IP:\n{diag_res.stdout}")

    except Exception as e:
        logger.error(f"Strategy C exception: {str(e)}", exc_info=True)

    logger.warning("Strategy C failed.")
    return None

def main():
    logger.info("="*30 + " NEW SESSION " + "="*30)
    if len(sys.argv) < 2:
        logger.error("No URL provided. Usage: python transcribe.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id(url)
    if not video_id:
        logger.error(f"Invalid URL: {url}")
        return

    logger.info(f"STARTING PROCESSING: Video ID {video_id}")

    transcript = fetch_via_ytdlp(url, video_id)

    if transcript:
        output_file = f"transcript_{video_id}.txt"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcript)
            logger.info(f"SUCCESS! Transcript saved to: {output_file}")

            # Print preview to console via logger
            logger.info("TRANSCRIPT PREVIEW (First 200 chars): " + transcript[:200] + "...")
        except Exception as e:
            logger.error(f"Failed to save output file: {str(e)}", exc_info=True)
    else:
        logger.error("CRITICAL FAILURE: All extraction methods failed to retrieve a transcript.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
        sys.exit(1)
