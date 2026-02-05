import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directories to sys.path to allow imports from transcribe_service
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..', '..')
sys.path.append(os.path.join(current_dir, '..', 'transcribe_service'))

from logger import log_api_activity, log_unique_visit
# We'll import transcribe logic later when we ensure it's exportable

app = Flask(__name__)
CORS(app)

PROMPT_FILE = os.path.join(current_dir, '..', 'transcribe_service', 'prompt_for_summary.txt')

@app.before_request
def before_request_logging():
    # log_api_activity will be called at the end to include status code
    pass

@app.after_request
def after_request_logging(response):
    log_api_activity(request.method, request.path, response.status_code)
    return response

@app.route('/health', methods=['GET'])
def health_check():
    # Log unique visit
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    log_unique_visit(client_ip, user_agent)
    
    return jsonify({"status": "ok"})

@app.route('/get_version', methods=['GET'])
def get_version():
    try:
        # Version file is at project root (2 levels up from src/backend/api)
        version_file = os.path.join(current_dir, '..', '..', '..', 'version')
        if not os.path.exists(version_file):
            return jsonify({"version": "unknown"}), 404
            
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
            
        return jsonify({"version": version})
    except Exception as e:
        log_api_activity('GET', '/get_version', 500, str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/get_summary_prompt', methods=['GET'])
def get_summary_prompt():
    try:
        if not os.path.exists(PROMPT_FILE):
            log_api_activity('GET', '/get_summary_prompt', 404, "Prompt file not found")
            return jsonify({"error": "Prompt file not found"}), 404
            
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({"summary_prompt": content})
    except Exception as e:
        log_api_activity('GET', '/get_summary_prompt', 500, str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/transcribe_yt_video', methods=['POST'])
def transcribe_video():
    data = request.json
    video_url = data.get('videoUrl')
    
    if not video_url:
        return jsonify({"error": "No videoUrl provided"}), 400
        
    try:
        # We'll call the transcribe logic here.
        # For now, let's prepare the integration.
        from transcribe import extract_video_id, fetch_via_python_api, fetch_via_cli_api, fetch_via_ytdlp
        
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400
            
        # Prioritized strategies as in transcribe.py
        transcript = fetch_via_python_api(video_id)
        if not transcript:
            transcript = fetch_via_cli_api(video_id)
        if not transcript:
            transcript = fetch_via_ytdlp(video_url, video_id)
            
        if transcript:
            return jsonify({"video_transcript": transcript})
        else:
            return jsonify({"error": "Transcription failed"}), 500
            
    except Exception as e:
        log_api_activity('POST', '/transcribe_yt_video', 500, str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Default Flask port is 5000 as per specification
    app.run(host='0.0.0.0', port=5000, debug=True)
