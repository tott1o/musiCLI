"""
Command-line interface for MusiCLI.

Handles argument parsing and launches the Textual application.
"""

import sys
from pathlib import Path

from .app import MusiCLIApp
from .state import AppState


def main():
    """Main entry point for the MusiCLI application."""
    # Initialize state to check for last-saved root
    state = AppState()

    # Get root path from command line or use last saved root
    root_path = ""
    if len(sys.argv) > 1:
        # Check if the first argument is a directory
        potential_path = sys.argv[1]
        if Path(potential_path).is_dir():
            root_path = str(Path(potential_path).resolve())
        else:
            # Maybe they passed a flag or just a wrong path?
            # For now, we assume it's the music folder if it's the only arg.
            print(f"Warning: '{potential_path}' is not a valid directory.")
            # Fallback to last root if available
            root_path = state.last_root
    else:
        # No arguments – use the last-saved root folder
        root_path = state.last_root

    # Launch the app
    app = MusiCLIApp(root_path=root_path)
    try:
        app.run()
    except Exception as e:
        print(f"Error launching MusiCLI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
