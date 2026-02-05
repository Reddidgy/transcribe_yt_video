import os
import sys
import re
import subprocess
import time
import logging
from logging.handlers import RotatingFileHandler

# Setup Logging
def setup_logger():
    # Ensure logs directory exists (now in the same dir as the script for reliability)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(current_dir, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "transcribe.log")

    # clean log file
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except Exception as e:
            print(f"Warning: Failed to clean log file: {str(e)}")

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
        paths = site.getsitepackages() if hasattr(site, 'getsitepackages') else []
        if hasattr(site, 'getusersitepackages'):
            paths.append(site.getusersitepackages())
        return paths
    except:
        return []

def ensure_dependencies(dep_name=None, force_upgrade=False):
    global _DEPS_PROCESSED
    deps = [dep_name] if dep_name else ["pytubefix", "openai-whisper", "ffmpeg-python", "setuptools"]

    for dep in deps:
        if dep in _DEPS_PROCESSED and not force_upgrade:
            continue

        # Import mapping
        module_map = {
            "openai-whisper": "whisper",
            "ffmpeg-python": "ffmpeg"
        }
        module_name = module_map.get(dep, dep.replace("-", "_"))

        try:
            if force_upgrade: raise ImportError("Forced upgrade requested")
            __import__(module_name)
        except ImportError:
            logger.info(f"Dependency '{dep}' missing or upgrade requested. Attempting install...")
            try:
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", dep]
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

def check_ffmpeg():
    """Verify that FFmpeg is installed as it's required for Whisper and pytubefix."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg NOT FOUND! It is required for transcription.")
        if os.name == 'nt':
            logger.info("Windows: Install via 'winget install ffmpeg' or download from ffmpeg.org")
        else:
            logger.info("Ubuntu: Install via 'sudo apt update && sudo apt install ffmpeg'")
        return False

def initialize_service():
    """Run initial environment checks."""
    ensure_dependencies()
    return check_ffmpeg()

if __name__ == "__main__":
    # Run initial checks only during CLI execution
    if not initialize_service():
        sys.exit(1)

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

def fetch_audio_and_transcribe(url, video_id):
    """Downloads audio via pytubefix and transcribes via OpenAI Whisper."""
    import pytubefix
    import whisper
    
    temp_audio = None
    try:
        logger.info(f"Starting process for Video ID: {video_id}")
        
        # Audio Extraction via pytubefix
        yt = pytubefix.YouTube(url)
        # Get highest quality audio stream
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            logger.error("No audio stream found for this video.")
            return None
            
        logger.info(f"Downloading audio: {yt.title}")
        temp_audio = audio_stream.download(filename=f"audio_{video_id}.m4a")
        logger.info(f"Audio downloaded to: {temp_audio}")
        
        # STT via Whisper
        logger.info("Loading Whisper model (base)...")
        model = whisper.load_model("base")
        
        logger.info("Transcribing audio (this may take a minute)...")
        result = model.transcribe(temp_audio)
        
        transcript = result.get("text", "").strip()
        
        if transcript:
            logger.info("Transcription SUCCESS!")
            return transcript
        else:
            logger.warning("Whisper returned empty transcript.")
            return None
            
    except Exception as e:
        logger.error(f"Error during audio processing/transcription: {str(e)}", exc_info=True)
        return None
    finally:
        # Cleanup
        if temp_audio and os.path.exists(temp_audio):
            try:
                os.remove(temp_audio)
                logger.info("Temporary audio file cleaned up.")
            except Exception as e:
                logger.warning(f"Failed to delete temp audio {temp_audio}: {str(e)}")

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

    transcript = fetch_audio_and_transcribe(url, video_id)

    if transcript:
        output_file = f"transcript_{video_id}.txt"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcript)
            logger.info(f"SUCCESS! Transcript saved to: {output_file}")
            logger.info("TRANSCRIPT PREVIEW (First 200 chars): " + transcript[:200] + "...")
        except Exception as e:
            logger.error(f"Failed to save output file: {str(e)}", exc_info=True)
    else:
        logger.error("CRITICAL FAILURE: Failed to retrieve a transcript.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
        sys.exit(1)
