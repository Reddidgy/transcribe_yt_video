import os
import sys
import threading
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directories to sys.path to allow imports from transcribe_service and shared logger
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.append(os.path.join(current_dir, '..', 'transcribe_service'))
sys.path.append(os.path.join(current_dir, '..'))

# Load environment variables from project root
load_dotenv(os.path.join(project_root, '.env'))

from logger import log_api_activity, log_visit, get_visits_count

app = Flask(__name__)
CORS(app)

PROMPT_FILE = os.path.join(current_dir, '..', 'transcribe_service', 'prompt_for_summary.txt')

# Sequential queue using a semaphore
transcription_semaphore = threading.Semaphore(1)

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
        log_visit(client_ip, user_agent)

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

@app.route('/get_visits_count', methods=['GET'])
def get_visits_count_endpoint():
    try:
        count = get_visits_count()
        return jsonify({"visits_count": count})
    except Exception as e:
        log_api_activity('GET', '/get_visits_count', 500, str(e))
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
        
    # Queue management
    acquired = transcription_semaphore.acquire(blocking=True)
    try:
        hard_api_host = os.getenv('HARD_API_HOST')
        if not hard_api_host:
            return jsonify({"error": "HARD_API_HOST not configured"}), 500
            
        # Ensure the URL is properly formatted for the Hard API
        hard_api_url = f"{hard_api_host.rstrip('/')}/transcribe_yt_video"
        
        # Proxy request to Hard API
        response = requests.post(
            hard_api_url,
            json={"videoUrl": video_url},
            timeout=1800  # Long timeout for transcription
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error_msg = response.json().get('error', 'Hard API request failed')
            log_api_activity('POST', '/transcribe_yt_video', response.status_code, error_msg)
            return jsonify({"error": error_msg}), response.status_code
            
    except requests.exceptions.RequestException as e:
        log_api_activity('POST', '/transcribe_yt_video', 500, str(e))
        return jsonify({"error": f"Failed to connect to Hard API: {str(e)}"}), 500
    except Exception as e:
        log_api_activity('POST', '/transcribe_yt_video', 500, str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        if acquired:
            transcription_semaphore.release()

if __name__ == '__main__':
    # Shared PORT 4520 as per specification
    port = int(os.getenv('PORT', 4520))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
