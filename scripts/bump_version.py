import os
import subprocess
import sys

def bump_version():
    version_file = os.path.join(os.path.dirname(__file__), '..', 'version')
    
    if not os.path.exists(version_file):
        print(f"Error: {version_file} not found.")
        sys.exit(1)
        
    try:
        with open(version_file, 'r') as f:
            version_str = f.read().strip()
            
        parts = version_str.split('.')
        if len(parts) != 3:
            print(f"Error: Invalid version format '{version_str}'. Expected X.Y.Z.")
            sys.exit(1)
            
        # Increment patch version
        major, minor, patch = map(int, parts)
        new_version = f"{major}.{minor}.{patch + 1}"
        
        with open(version_file, 'w') as f:
            f.write(new_version)
            
        print(f"Bumped version from {version_str} to {new_version}")
        
        # Add to git index
        subprocess.run(['git', 'add', version_file], check=True)
        
    except Exception as e:
        print(f"Error updating version: {e}")
        sys.exit(1)

if __name__ == "__main__":
    bump_version()
