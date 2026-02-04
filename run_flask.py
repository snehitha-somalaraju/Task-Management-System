#!/usr/bin/env python
"""Flask API server launcher with proper error handling"""
import sys
import os

os.chdir(r'f:\Projects\task-management-system')

try:
    from flask_api import app
    
    if __name__ == '__main__':
        print("\n" + "=" * 70)
        print("TASK MANAGEMENT SYSTEM - FLASK API".center(70))
        print("=" * 70)
        print("\n[OK] Starting Flask API server...")
        print("[OK] API available at: http://localhost:5000")
        print("[OK] Dashboard available at: http://localhost:5000/dashboard")
        print("[OK] Google Calendar Sync available at: /api/calendar/*")
        print("\n" + "=" * 70 + "\n")
        
        # Use threaded mode to keep app running
        try:
            app.run(debug=False, port=5000, host='0.0.0.0', use_reloader=False, threaded=True)
        except KeyboardInterrupt:
            print("\n[OK] Server stopped by user")
            sys.exit(0)
        except Exception as run_error:
            print(f"[ERROR] Runtime error: {run_error}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
except Exception as e:
    print(f"[ERROR] Failed to start Flask: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
