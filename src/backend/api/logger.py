import os
import datetime
import json

LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
VISITS_DIR = os.path.join(os.path.dirname(__file__), 'user_visits_logs')

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(VISITS_DIR, exist_ok=True)

def log_api_activity(method, endpoint, status_code, message=""):
    """Logs general API activity to src/backend/api/logs."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {method} {endpoint} - Status: {status_code} - {message}\n"
    
    log_file = os.path.join(LOGS_DIR, f"api_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def log_unique_visit(ip, user_agent):
    """Logs unique user visits to src/backend/api/user_visits_logs."""
    visit_file = os.path.join(VISITS_DIR, 'visits.json')
    
    visits = []
    if os.path.exists(visit_file):
        try:
            with open(visit_file, 'r', encoding='utf-8') as f:
                visits = json.load(f)
        except (json.JSONDecodeError, ValueError):
            visits = []

    # Check for uniqueness based on IP and User-Agent
    is_unique = True
    for v in visits:
        if v.get('ip') == ip and v.get('user_agent') == user_agent:
            is_unique = False
            break
            
    if is_unique:
        new_visit = {
            "ip": ip,
            "user_agent": user_agent,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        visits.append(new_visit)
        with open(visit_file, 'w', encoding='utf-8') as f:
            json.dump(visits, f, indent=4)
        return True
    return False
