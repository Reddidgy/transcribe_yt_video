#!/bin/bash

# Getting the directory of the script!!!
script_path=$(realpath "$0")
dir=$(dirname "$script_path")

# Move to the directory of the repository
cd "$dir" || { echo "Failed to change directory to script location"; exit 1; }

# Move to the root directory of the repository
repo_root=$(pwd)
echo "Repository root: $repo_root"

# Ensure git is installed
if ! command -v git &> /dev/null; then
    echo "git could not be found. Please install git."
    exit 1
fi

# Define the branch name as a variable after confirming we're in a Git repository
BRANCH_NAME=$(git branch --show-current)
echo "$BRANCH_NAME"
if [ -z "$BRANCH_NAME" ]; then
    echo "Failed to determine the current branch. Ensure this is a valid git repository."
    exit 1
fi

git checkout "$BRANCH_NAME"

# Fetch and pull changes from the remote repository
while true; do
    # Monitor for changes in the remote repository
    git fetch origin

    # Check for divergence from the remote branch
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse "@{u}")
    BASE=$(git merge-base @ "@{u}")

    if [ "$LOCAL" = "$REMOTE" ]; then
        TEMPVAR="Already up-to-date"
    elif [ "$LOCAL" = "$BASE" ]; then
        echo "Need to pull changes, rebasing..."
        git pull --rebase origin "$BRANCH_NAME"
    else
        echo "Resetting local branch to match remote..."
        git reset --hard "origin/$BRANCH_NAME"
    fi

    # Wait for 5 seconds before fetching again
    sleep 5
done
