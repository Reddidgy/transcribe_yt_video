import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directories to sys.path to allow imports from transcribe_service
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.append(os.path.join(current_dir, '..', 'transcribe_service'))

# Load environment variables from project root
load_dotenv(os.path.join(project_root, '.env'))

from logger import log_api_activity

app = Flask(__name__)
CORS(app)

@app.before_request
def before_request_logging():
    pass

@app.after_request
def after_request_logging(response):
    if request.method != 'OPTIONS':
        log_api_activity(request.method, request.path, response.status_code)
    return response

@app.route('/get_version', methods=['GET'])
def get_version():
    try:
        # Log visit
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')

        # Version file is at project root
        version_file = os.path.join(current_dir, '..', '..', '..', 'version')
        if not os.path.exists(version_file):
            return jsonify({"version": "unknown"}), 404

        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()

        return jsonify({"version": version})
    except Exception as e:
        log_api_activity('GET', '/get_version', 500, str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/transcribe_yt_video', methods=['POST'])
def transcribe_video():
    data = request.json
    video_url = data.get('videoUrl')
    
    if not video_url:
        return jsonify({"error": "No videoUrl provided"}), 400
        
    try:
        from transcribe import extract_video_id, fetch_audio_and_transcribe, initialize_service
        
        # Ensure service is initialized (dependencies and ffmpeg check)
        initialize_service()
        
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400
            
        # Call the transcription logic
        transcript = fetch_audio_and_transcribe(video_url, video_id)
            
        if transcript:
            return jsonify({"video_transcript": transcript})
        else:
            return jsonify({"error": "Transcription failed. Check backend logs for details."}), 500
            
    except Exception as e:
        log_api_activity('POST', '/transcribe_yt_video', 500, str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Shared PORT 4520 as per specification
    port = int(os.getenv('PORT', 4520))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
