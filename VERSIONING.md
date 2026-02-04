# Versioning System

This project uses an automated versioning system to track changes.

## How it Works

The version is stored in the `version` file in the root directory.

### Automated Patch Updates (0.0.X)

A Git `pre-commit` hook is configured to automatically increment the patch version (the third number) on every commit.

1.  When you run `git commit`, the hook triggers `scripts/bump_version.py`.
2.  The script reads the current version, increments the patch number.
3.  The updated `version` file is automatically added to your commit (`git add version`).

### Manual Version Updates (X.X.0)

If you want to increment the **Major** or **Minor** version, you should manually update the `version` file before committing.

-   **Minor Update**: Change `0.0.5` to `0.1.0`. The next commit will then become `0.1.1`.
-   **Major Update**: Change `0.1.5` to `1.0.0`. The next commit will then become `1.0.1`.

## Requirements

-   **Python**: The versioning script requires Python to be installed and available in your PATH as `python`.
-   **Cross-Platform**: This system is designed to work on both Windows and MacOS/Linux.
