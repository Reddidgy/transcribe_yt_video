import os
import sys
import re
import subprocess
import json
import time

def extract_video_id(url):
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

def fetch_via_python_api(video_id):
    """Strategy A: Direct Python import (cleanest)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # Fallback to ru if en is missing (common for this user's videos)
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ru'])
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        print(f"[*] Python API method failed: {e}")
        return None

def fetch_via_cli_api(video_id):
    """Strategy B: Subprocess call to CLI (bypasses attribute errors in some environments)."""
    print("[*] Trying CLI-based API fetch...")
    try:
        # We try to get it in JSON format for easy parsing
        cmd = [sys.executable, "-m", "youtube_transcript_api", video_id, "--format", "json", "--languages", "en", "ru"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # CLI often returns a list of transcripts if multiple languages are passed
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                target_list = data[0]
            else:
                target_list = data
            return " ".join([item['text'] for item in target_list])
    except Exception as e:
        print(f"[*] CLI API method failed: {e}")
    return None

def fetch_via_ytdlp(url, video_id):
    """Strategy C: yt-dlp fallback (extracts VTT)."""
    print("[*] Trying yt-dlp fallback...")
    prefix = f"sub_{video_id}_{int(time.time())}"
    cmd = ["yt-dlp", "--write-auto-sub", "--skip-download", "--sub-langs", "en,ru", "-o", prefix, url]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        # Find the VTT file
        for f in os.listdir("."):
            if f.startswith(prefix) and f.endswith(".vtt"):
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read()
                # Simple cleanup
                text = re.sub(r'<[^>]+>', '', content)
                text = " ".join([l.strip() for l in text.splitlines() if l.strip() and "-->" not in l and not l.isdigit() and "WEBVTT" not in l])
                os.remove(f)
                return text
    except:
        pass
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <youtube_url>")
        sys.exit(1)
        
    url = sys.argv[1]
    video_id = extract_video_id(url)
    if not video_id:
        print(f"[!] Invalid URL: {url}")
        return

    print(f"[*] Processing Video ID: {video_id}")
    
    # Try prioritized strategies
    transcript = fetch_via_python_api(video_id)
    if not transcript:
        transcript = fetch_via_cli_api(video_id)
    if not transcript:
        transcript = fetch_via_ytdlp(url, video_id)
        
    if transcript:
        output_file = f"transcript_{video_id}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcript)
        print("\n" + "="*50)
        print("TRANSCRIPT PREVIEW:")
        print("="*50)
        print(transcript[:500] + "...")
        print("="*50)
        print(f"\n[*] SUCCESS! Saved to: {output_file}")
    else:
        print("[!] All extraction methods failed.")

if __name__ == "__main__":
    main()
