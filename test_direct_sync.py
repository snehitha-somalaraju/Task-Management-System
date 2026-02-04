#!/usr/bin/env python3
"""
Direct Calendar Sync Test - Tests without Flask
"""

from database import Database
from google_calendar_sync import GoogleCalendarSync

print("\n" + "="*70)
print("DIRECT CALENDAR SYNC TEST".center(70))
print("="*70 + "\n")

# Test 1: Initialize database
print("[TEST 1] Initializing database...")
try:
    db = Database("tasks.db")
    print("✓ Database initialized")
except Exception as e:
    print(f"✗ Database error: {e}")
    exit(1)

# Test 2: Initialize Google Calendar Sync
print("\n[TEST 2] Initializing Google Calendar Sync...")
try:
    sync = GoogleCalendarSync(db)
    print("✓ GoogleCalendarSync initialized")
    print(f"  - Credentials file: {sync.credentials_file}")
    print(f"  - Token file: {sync.token_file}")
    print(f"  - Mapping file: {sync.mapping_file}")
except Exception as e:
    print(f"✗ Sync initialization error: {e}")
    exit(1)

# Test 3: Check credentials file
print("\n[TEST 3] Checking credentials...")
import os
if os.path.exists(sync.credentials_file):
    print(f"✓ Credentials file found: {sync.credentials_file}")
    # Read first part of file to verify it's valid JSON
    try:
        import json
        with open(sync.credentials_file, 'r') as f:
            creds = json.load(f)
        print(f"✓ Credentials JSON is valid")
        print(f"  - Client ID: {creds.get('web', {}).get('client_id', 'N/A')[:20]}...")
    except Exception as e:
        print(f"✗ Error reading credentials: {e}")
else:
    print(f"✗ Credentials file not found: {sync.credentials_file}")

# Test 4: Check if already authenticated
print("\n[TEST 4] Checking authentication status...")
if os.path.exists(sync.token_file):
    print(f"✓ Token file exists (previously authenticated)")
else:
    print(f"→ Token file not found (first time setup)")

# Test 5: Create a test task
print("\n[TEST 5] Creating test task...")
try:
    from task_manager import TaskManager
    tm = TaskManager(db)
    task_id = tm.create_task(
        title="TEST: Google Calendar Sync",
        description="Test task for calendar sync",
        priority="high"
    )
    print(f"✓ Test task created with ID: {task_id}")
except Exception as e:
    print(f"✗ Error creating task: {e}")
    exit(1)

# Test 6: Test task-to-event conversion
print("\n[TEST 6] Testing task-to-event conversion...")
try:
    event_body = sync._task_to_event(task_id)
    print(f"✓ Task converted to calendar event format")
    print(f"  - Title: {event_body.get('summary', 'N/A')}")
    print(f"  - Description: {event_body.get('description', 'N/A')[:50]}...")
    print(f"  - Color ID: {event_body.get('colorId', 'N/A')}")
except Exception as e:
    print(f"✗ Error converting task: {e}")

# Test 7: Check mapping storage
print("\n[TEST 7] Checking task-event mapping...")
print(f"  - Mapping file: {sync.mapping_file}")
print(f"  - Mapping data: {sync.task_event_map}")
if os.path.exists(sync.mapping_file):
    print(f"✓ Mapping file exists")
else:
    print(f"→ Mapping file will be created on first sync")

print("\n" + "="*70)
print("NEXT STEPS:".center(70))
print("="*70)
print("""
1. Keep Flask running:
   python "f:\\Projects\\task-management-system\\run_flask.py"

2. Authenticate with Google Calendar:
   curl.exe -X POST "http://localhost:5000/api/calendar/authenticate"
   (Opens browser for Google login)

3. Create and sync a task:
   - Create task via API or dashboard
   - Call /api/calendar/sync/all to sync all tasks

4. Check Google Calendar:
   https://calendar.google.com
""")
print("="*70 + "\n")
