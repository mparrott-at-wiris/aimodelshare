#!/usr/bin/env python
"""
Manual test script for Bias Detective app with test_mode enabled.
This script launches the app and provides a URL that includes the session ID.

Usage:
    python test_bias_detective_with_session.py
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aimodelshare.moral_compass.apps.bias_detective import launch_bias_detective_app

if __name__ == "__main__":
    # Session ID for testing
    SESSION_ID = "953144fd-ad3a-4d14-b0bb-43ee598787e2"
    
    print("=" * 80)
    print("Launching Bias Detective App with Test Mode Enabled")
    print("=" * 80)
    print()
    print(f"Session ID: {SESSION_ID}")
    print()
    print("After the app starts, access it with the session ID parameter:")
    print(f"  http://127.0.0.1:8080/?sessionid={SESSION_ID}")
    print()
    print("Test Mode Features:")
    print("  - Debug panel visible at the bottom showing:")
    print("    * Initial load: Score, Rank, Team Rank, Completed Task IDs")
    print("    * Quiz submissions: Previous vs new task IDs, score delta, rank changes")
    print("    * Navigation: Current data after navigation")
    print("  - Server logs printed for each interaction")
    print()
    print("=" * 80)
    print()
    
    # Launch the app with test_mode=True
    launch_bias_detective_app(
        share=False,
        server_name="127.0.0.1",
        server_port=8080,
        test_mode=True
    )
