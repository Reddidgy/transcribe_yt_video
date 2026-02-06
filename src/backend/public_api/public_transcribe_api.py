import os
import sys
import threading
import uuid
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

from logger import log_api_activity, log_visit, get_visits_count, log_event

app = Flask(__name__)
CORS(app)

PROMPT_FILE = os.path.join(current_dir, '..', 'transcribe_service', 'prompt_for_summary.txt')

# In-memory storage for tasks status and results
# Format: { task_id: { "status": "processing" | "completed" | "error", "result": "...", "error": "..." } }
tasks = {}
tasks_lock = threading.Lock()

# Sequential queue using a semaphore
transcription_semaphore = threading.Semaphore(1)

@app.before_request
def before_request_logging():
    pass

@app.after_request
def after_request_logging(response):
    if request.method != 'OPTIONS':
        payload = None
        if request.is_json:
            payload = request.get_json(silent=True)
            # Mask sensitive data if any
        log_api_activity('public_api', request.method, request.path, response.status_code, payload=payload)
    return response

@app.route('/get_version', methods=['GET'])
def get_version():
    try:
        # Log visit
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        log_visit(client_ip, user_agent)

        version_file = os.path.join(current_dir, '..', '..', '..', 'version')
        if not os.path.exists(version_file):
            return jsonify({"version": "unknown"}), 404
            
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
            
        return jsonify({"version": version})
    except Exception as e:
        log_api_activity('public_api', 'GET', '/get_version', 500, str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/get_visits_count', methods=['GET'])
def get_visits_count_endpoint():
    try:
        count = get_visits_count()
        return jsonify({"visits_count": count})
    except Exception as e:
        log_api_activity('public_api', 'GET', '/get_visits_count', 500, str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/get_summary_prompt', methods=['GET'])
def get_summary_prompt():
    try:
        if not os.path.exists(PROMPT_FILE):
            log_api_activity('public_api', 'GET', '/get_summary_prompt', 404, "Prompt file not found")
            return jsonify({"error": "Prompt file not found"}), 404
            
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({"summary_prompt": content})
    except Exception as e:
        log_api_activity('public_api', 'GET', '/get_summary_prompt', 500, str(e))
        return jsonify({"error": str(e)}), 500

def run_transcription_background(task_id, video_url):
    """Background thread function to handle Hard API transcription with semaphore."""
    with tasks_lock:
        tasks[task_id]["status"] = "processing"

    acquired = transcription_semaphore.acquire(blocking=True)
    try:
        hard_api_host = os.getenv('HARD_API_HOST')
        if not hard_api_host:
            with tasks_lock:
                tasks[task_id] = {"status": "error", "error": "HARD_API_HOST not configured"}
            return
            
        hard_api_url = f"{hard_api_host.rstrip('/')}/transcribe_yt_video"
        
        # Proxy request to Hard API
        response = requests.post(
            hard_api_url,
            json={"videoUrl": video_url},
            timeout=1800  # Long timeout for transcription
        )
        
        with tasks_lock:
            if response.status_code == 200:
                tasks[task_id] = {"status": "completed", "result": response.json().get("video_transcript")}
            else:
                error_msg = response.json().get('error', 'Hard API request failed')
                tasks[task_id] = {"status": "error", "error": error_msg}
                log_api_activity('public_api', 'BACKGROUND_POST', '/transcribe_yt_video', response.status_code, error_msg, payload={"videoUrl": video_url})
                
    except requests.exceptions.RequestException as e:
        with tasks_lock:
            tasks[task_id] = {"status": "error", "error": f"Failed to connect to Hard API: {str(e)}"}
        log_api_activity('public_api', 'BACKGROUND_POST', '/transcribe_yt_video', 500, str(e), payload={"videoUrl": video_url})
    except Exception as e:
        with tasks_lock:
            tasks[task_id] = {"status": "error", "error": str(e)}
        log_api_activity('public_api', 'BACKGROUND_POST', '/transcribe_yt_video', 500, str(e), payload={"videoUrl": video_url})
    finally:
        if acquired:
            transcription_semaphore.release()

@app.route('/transcribe_yt_video', methods=['POST'])
def transcribe_video():
    data = request.json
    video_url = data.get('videoUrl')
    
    if not video_url:
        return jsonify({"error": "No videoUrl provided"}), 400
        
    task_id = str(uuid.uuid4())
    
    with tasks_lock:
        tasks[task_id] = {"status": "pending"}
        
    # Start background thread
    threading.Thread(target=run_transcription_background, args=(task_id, video_url)).start()
    
    return jsonify({"task_id": task_id}), 202

@app.route('/transcribe_status/<task_id>', methods=['GET'])
def get_transcribe_status(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    return jsonify(task)

if __name__ == '__main__':
    # Shared PORT 4520 as per specification
    port = int(os.getenv('PORT', 4520))
    host = os.getenv('HOST', '0.0.0.0')
    log_event('public_api', f"Public API starting on {host}:{port}")
    try:
        app.run(host=host, port=port, debug=False) # debug=False to avoid double thread start in some envs
    finally:
        log_event('public_api', "Public API stopped")
