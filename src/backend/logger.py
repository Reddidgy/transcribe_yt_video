import os
import datetime
import json

LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
VISITS_DIR = os.path.join(os.path.dirname(__file__), 'user_visits_logs')

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(VISITS_DIR, exist_ok=True)

def log_api_activity(method, endpoint, status_code, message=""):
    """Logs general API activity to src/backend/logs."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {method} {endpoint} - Status: {status_code} - {message}\n"
    
    log_file = os.path.join(LOGS_DIR, f"api_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def log_visit(ip, user_agent):
    """
    Logs every user visit.
    Increments total count in visits_count and logs unique info in unique_visits.json.
    """
    count_file = os.path.join(VISITS_DIR, 'visits_count')
    unique_file = os.path.join(VISITS_DIR, 'unique_visits.json')
    
    # 1. Update total visits count (simple int)
    count = 0
    if os.path.exists(count_file):
        try:
            with open(count_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                count = int(content) if content else 0
        except (ValueError, IOError):
            count = 0
            
    count += 1
    with open(count_file, 'w', encoding='utf-8') as f:
        f.write(str(count))

    # 2. Update unique visits JSON
    unique_visits = []
    if os.path.exists(unique_file):
        try:
            with open(unique_file, 'r', encoding='utf-8') as f:
                unique_visits = json.load(f)
        except (json.JSONDecodeError, ValueError):
            unique_visits = []

    # Check for uniqueness based on IP and User-Agent
    is_unique = True
    for v in unique_visits:
        if v.get('ip') == ip and v.get('user_agent') == user_agent:
            is_unique = False
            break
            
    if is_unique:
        new_unique = {
            "ip": ip,
            "user_agent": user_agent,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        unique_visits.append(new_unique)
        with open(unique_file, 'w', encoding='utf-8') as f:
            json.dump(unique_visits, f, indent=4)
            
    return True

def get_visits_count():
    """Returns the total count from user_visits_logs/visits_count."""
    count_file = os.path.join(VISITS_DIR, 'visits_count')
    if not os.path.exists(count_file):
        return 0
    try:
        with open(count_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return int(content) if content else 0
    except (ValueError, IOError):
        return 0
