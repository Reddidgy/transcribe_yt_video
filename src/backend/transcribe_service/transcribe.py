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
        
        # Defensive check for the method
        if not hasattr(YouTubeTranscriptApi, 'get_transcript'):
            print(f"[*] Python API: YouTubeTranscriptApi missing 'get_transcript'. Trying list_transcripts...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Find manually created or auto-generated
            try:
                t_obj = transcript_list.find_transcript(['en', 'ru'])
            except:
                t_obj = transcript_list.find_generated_transcript(['en', 'ru'])
            transcript = t_obj.fetch()
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ru'])
            
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        print(f"[*] Python API method failed: {e}")
        return None

def fetch_via_cli_api(video_id):
    """Strategy B: Subprocess call to CLI (handles noise like deprecation warnings)."""
    print("[*] Trying CLI-based API fetch...")
    try:
        cmd = [sys.executable, "-m", "youtube_transcript_api", video_id, "--format", "json", "--languages", "en", "ru"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        output = result.stdout.strip()
        if not output:
            return None
            
        # ROBUST JSON EXTRACTION: Find the first '[' or '{' to skip diagnostic noise
        start_idx = -1
        for i, char in enumerate(output):
            if char in '[{':
                start_idx = i
                break
        
        if start_idx == -1:
            print(f"[*] CLI API: No JSON structure found in output.")
            return None
            
        clean_json = output[start_idx:]
        data = json.loads(clean_json)
        
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
    # Use a unique prefix to avoid collisions
    prefix = f"sub_{video_id}_{int(time.time())}"
    # --buffer-size for speed, --no-warnings to reduce noise (though we capture output anyway)
    cmd = ["yt-dlp", "--write-auto-sub", "--skip-download", "--sub-langs", "en,ru", "--no-warnings", "-o", prefix, url]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        # Find the VTT file - yt-dlp might append .en.vtt or .ru.vtt
        vtt_file = None
        for f in os.listdir("."):
            if f.startswith(prefix) and f.endswith(".vtt"):
                vtt_file = f
                break
                
        if vtt_file:
            with open(vtt_file, "r", encoding="utf-8") as file:
                content = file.read()
            
            # More robust VTT parsing: strip labels, timestamps, and metadata
            lines = content.splitlines()
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or "-->" in line or line.isdigit() or "WEBVTT" in line or "Kind:" in line or "Language:" in line:
                    continue
                # Remove inline tags like <c.color> or 00:00:00.000
                line = re.sub(r'<[^>]+>', '', line)
                if line:
                    text_lines.append(line)
            
            os.remove(vtt_file)
            return " ".join(text_lines)
    except Exception as e:
        print(f"[*] yt-dlp method failed: {e}")
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
