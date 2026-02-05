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

def fetch_via_python_api(video_id):
    """Strategy A: Direct Python import (cleanest)."""
    logger.info(f"Attempting Strategy A: Direct Python API for ID: {video_id}")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # Fallback to ru if en is missing (common for this user's videos)
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ru'])
        logger.info("Strategy A SUCCESS!")
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        logger.warning(f"Strategy A failed: {str(e)}")
        return None

def fetch_via_cli_api(video_id):
    """Strategy B: Subprocess call to CLI (bypasses attribute errors in some environments)."""
    logger.info(f"Attempting Strategy B: CLI-based API fetch for ID: {video_id}")
    try:
        # We try to get it in JSON format for easy parsing
        cmd = [sys.executable, "-m", "youtube_transcript_api", video_id, "--format", "json", "--languages", "en", "ru"]
        logger.info(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # CLI often returns a list of transcripts if multiple languages are passed
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                target_list = data[0]
            else:
                target_list = data
            logger.info("Strategy B SUCCESS!")
            return " ".join([item['text'] for item in target_list])
        else:
            logger.warning(f"Strategy B failed with return code {result.returncode}. Error: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"Strategy B exception: {str(e)}", exc_info=True)
    return None

def fetch_via_ytdlp(url, video_id):
    """Strategy C: yt-dlp fallback (extracts VTT)."""
    logger.info(f"Attempting Strategy C: yt-dlp fallback for URL: {url}")
    prefix = f"sub_{video_id}_{int(time.time())}"
    cmd = ["yt-dlp", "--write-auto-sub", "--skip-download", "--sub-langs", "en,ru", "-o", prefix, url]
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"yt-dlp returned non-zero code: {result.returncode}")
        
        # Find the VTT file
        for f in os.listdir("."):
            if f.startswith(prefix) and f.endswith(".vtt"):
                logger.info(f"Found subtitle file: {f}")
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read()
                # Simple cleanup
                text = re.sub(r'<[^>]+>', '', content)
                text = " ".join([l.strip() for l in text.splitlines() if l.strip() and "-->" not in l and not l.isdigit() and "WEBVTT" not in l])
                os.remove(f)
                logger.info("Strategy C SUCCESS!")
                return text
    except Exception as e:
        logger.error(f"Strategy C exception: {str(e)}", exc_info=True)
    
    logger.warning("Strategy C failed to find or parse subtitles.")
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

    # Try prioritized strategies
    transcript = fetch_via_python_api(video_id)
    if not transcript:
        transcript = fetch_via_cli_api(video_id)
    if not transcript:
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
