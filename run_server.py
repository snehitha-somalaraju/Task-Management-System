#!/usr/bin/env python
"""
Simple Flask server launcher
"""

import sys
import os
from flask_api import app

if __name__ == '__main__':
    print("\nStarting Flask API server...")
    print("Press Ctrl+C to stop\n")
    
    try:
        app.run(
            debug=False,
            port=5000,
            host='0.0.0.0',
            use_reloader=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
