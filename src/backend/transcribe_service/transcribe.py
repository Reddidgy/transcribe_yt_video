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

def fetch_via_python_api(video_id):
    """Strategy A: Direct Python import with Granular Fallback."""
    logger.info(f"Attempting Strategy A: Direct Python API for ID: {video_id}")
    
    def try_fetch():
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            # Log library path for diagnostics
            try:
                import youtube_transcript_api
                logger.info(f"Library path: {youtube_transcript_api.__file__}")
            except: pass

            # ATTEMPT 1: Try preferred languages
            try:
                return YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ru'])
            except:
                try:
                    return YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                except:
                    try:
                        return YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'])
                    except: pass
            
            # ATTEMPT 2: Granular API (List all and pick FIRST available)
            logger.info("Preferred native languages failed. Attempting to list all transcripts...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to pick anything
            try:
                # Get the first one in the list
                first = next(iter(transcript_list))
                logger.info(f"Picking fallback language: {first.language}")
                return first.fetch()
            except StopIteration:
                raise Exception("No transcripts found in any language for this video")

        except Exception as e:
            logger.debug(f"Strategy A inner error: {str(e)}")
            raise

    try:
        transcript_data = try_fetch()
        if transcript_data:
            logger.info("Strategy A SUCCESS!")
            return " ".join([t.get('text', '') for t in transcript_data if t.get('text')])
        return None
    except Exception as e:
        logger.warning(f"Strategy A failed: {str(e)}")
        # RESILIENCE: Avoid recursion, only repair once
        if ("get_transcript" in str(e) or "YouTubeTranscriptApi" in str(e) or "list_transcripts" in str(e)) and "youtube-transcript-api" not in _DEPS_PROCESSED:
             logger.info("Triggering Total Environment Conquest for Strategy A...")
             ensure_dependencies("youtube-transcript-api", force_upgrade=True)
             try:
                 nuclear_reload(["youtube_transcript_api"])
                 transcript_data = try_fetch()
                 if transcript_data:
                     logger.info("Strategy A RECONQUERED and SUCCESS!")
                     return " ".join([t.get('text', '') for t in transcript_data if t.get('text')])
             except Exception as repair_err:
                 logger.warning(f"Strategy A reconquest failed: {str(repair_err)}")
        return None

def fetch_via_cli_api(video_id):
    """Strategy B: Subprocess call to CLI via sys.executable."""
    logger.info(f"Attempting Strategy B: CLI-based API fetch for ID: {video_id}")
    try:
        cmd_variations = [
            [sys.executable, "-m", "youtube_transcript_api", video_id, "--format", "json", "--languages", "en", "ru"],
            [sys.executable, "-m", "youtube_transcript_api", video_id, "--format", "json"],
            [sys.executable, "-m", "youtube_transcript_api", video_id],
        ]
        
        env = os.environ.copy()
        stdout = ""
        stderr = ""
        returncode = 1
        
        for cmd in cmd_variations:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env, timeout=40)
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                returncode = result.returncode
                
                if returncode == 0 and stdout:
                    logger.info(f"Strategy B CLI succeeded: {' '.join(cmd)}")
                    break
            except Exception:
                continue
        
        if not stdout and not stderr: return None

        combined = "\n".join([stdout, stderr])
        
        # PARSING 1: JSON extraction
        match = re.search(r'(\[.*\]|\{.*\})', combined, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                target = data[0] if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list) else data
                if isinstance(target, list) and len(target) > 0 and 'text' in target[0]:
                    logger.info("Strategy B SUCCESS via JSON!")
                    return " ".join([item.get('text', '') for item in target if item.get('text')])
            except: pass

        # PARSING 2: Raw text fallback
        text_matches = re.findall(r"['\"]text['\"]:\s*['\"](.*?)['\"]", combined, re.DOTALL)
        if text_matches:
            logger.info("Strategy B SUCCESS via Raw Text!")
            return " ".join(text_matches)

        # PARSING 3: Line fallback
        lines = [l.strip() for l in combined.split('\n') if len(l.strip()) > 20 and not l.strip().startswith('{') and not l.strip().startswith('[')]
        if lines:
             logger.info("Strategy B SUCCESS via Line Heuristic!")
             return " ".join(lines)

    except Exception as e:
        logger.error(f"Strategy B exception: {str(e)}")
    return None

def fetch_via_ytdlp(url, video_id):
    """Strategy C: yt-dlp fallback with Mobile Spoofing & Relaxed Parsing."""
    logger.info(f"Attempting Strategy C: yt-dlp fallback for URL: {url}")
    env = os.environ.copy()
    
    def run_ytdlp():
        prefix = f"sub_{video_id}_{int(time.time())}"
        # STEALTH: Use mobile player clients to bypass bot checks
        base_cmds = [[sys.executable, "-m", "yt_dlp"], ["yt-dlp"]]
        args = [
            "--write-sub", "--write-auto-sub", "--skip-download", 
            "--sub-langs", "en,ru", "--no-check-certificate", "--geo-bypass",
            "--ignore-errors", "--user-agent", USER_AGENT, 
            "--add-header", f"Referer:{REFERER}",
            "--extractor-args", "youtube:player_client=android,web",
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

    # Surgically find the file
    downloaded_file = None
    if result.stdout:
        m = re.search(r'\[info\] Writing video subtitles to: (.*\.vtt|.*\.srt)', result.stdout)
        if m: downloaded_file = m.group(1).strip()

    try:
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
                
                # REFINED CLEANUP (Avoid massive deletion)
                # Remove VTT headers and timestamps
                text = re.sub(r'WEBVTT|KIND|LANGUAGE|FILE|NOTE.*?\n', '', content, flags=re.I)
                # Fix: NOTE.* can match across lines if not careful. Added ? to make it non-greedy or end at newline.
                text = re.sub(r'\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}.*?\n', '', text)
                text = re.sub(r'<[^>]+>', '', text)
                # Final join
                processed_text = " ".join([l.strip() for l in text.splitlines() if l.strip()])
                
                os.remove(file_path)
                if len(processed_text) > 5: # Relaxed threshold
                    logger.info("Strategy C SUCCESS!")
                    return processed_text
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {str(e)}")
        
        # Diagnostics on failure
        if result.returncode == 0:
            logger.warning("Strategy C: Exited successfully but no usable subtitles were extracted.")
            diag_cmd = [sys.executable, "-m", "yt_dlp", "--list-subs", url]
            diag_res = subprocess.run(diag_cmd, capture_output=True, text=True, encoding='utf-8', env=env)
            if diag_res.stdout: logger.info(f"Available subs diagnostic:\n{diag_res.stdout}")

    except Exception as e:
        logger.error(f"Strategy C exception: {str(e)}")
    
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
