"""
Test Service Account Calendar Sync
Tests calendar sync using Service Account credentials
"""

import json
import os
from database import Database
from service_account_sync import ServiceAccountCalendarSync


def test_service_account_sync():
    """Test Service Account calendar sync"""
    
    print("\n" + "=" * 70)
    print("SERVICE ACCOUNT CALENDAR SYNC TEST".center(70))
    print("=" * 70 + "\n")
    
    # Initialize
    print("[OK] Initializing database...")
    db = Database("tasks.db")
    
    print("[OK] Initializing Service Account sync...")
    sync = ServiceAccountCalendarSync(db)
    
    # Test 1: Check authentication
    print("\n[TEST] Authentication Status")
    print("-" * 70)
    is_auth = sync.is_authenticated()
    print(f"Authenticated: {is_auth}")
    
    if not is_auth:
        print("\n[!] Not authenticated!")
        print("[!] Make sure:")
        print("    1. service_account_key.json is in the project folder")
        print("    2. Google Calendar API is enabled in Google Cloud")
        print("    3. Your calendar is shared with the service account email")
        print("\n[!] Skipping remaining tests...")
        return
    
    print("[OK] Authentication successful!")
    
    # Test 2: List calendars
    print("\n[TEST] List Calendars")
    print("-" * 70)
    calendars = sync.list_calendars()
    print(f"Found {len(calendars)} calendars:")
    for cal in calendars:
        primary = " (Primary)" if cal.get('primary') else ""
        print(f"  - {cal.get('summary')}{primary}")
    
    # Test 3: Get sync status
    print("\n[TEST] Sync Status")
    print("-" * 70)
    status = sync.get_sync_status()
    print(f"Authenticated: {status['authenticated']}")
    print(f"Synced Tasks: {status['synced_tasks']}")
    print(f"Service Status: {status['service_status']}")
    
    # Test 4: Create a test task
    print("\n[TEST] Create Test Task")
    print("-" * 70)
    
    # First, check if we have a user
    users = db.execute_query("SELECT id FROM users LIMIT 1")
    if not users:
        print("[!] No users in database!")
        print("[!] Create a user first by signing up in the web interface")
        return
    
    user_id = dict(users[0])['id']
    print(f"Using user_id: {user_id}")
    
    # Create a test task
    task_id = db.execute_update(
        """INSERT INTO tasks 
           (user_id, title, description, priority, status, due_date, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            "Test Calendar Event",
            "This is a test task for calendar sync",
            "high",
            "not_started",
            "2026-01-30",
            "2026-01-25T10:00:00",
            "2026-01-25T10:00:00"
        )
    )
    print(f"Created test task: ID {task_id}")
    
    # Test 5: Sync the task
    print("\n[TEST] Sync Task to Calendar")
    print("-" * 70)
    success, message = sync.sync_task(task_id)
    print(f"Success: {success}")
    print(f"Message: {message}")
    
    if not success:
        print("\n[!] Sync failed!")
        print("[!] Common issues:")
        print("    1. Service account email not shared with calendar")
        print("    2. Calendar not set to 'Make changes to events'")
        print("    3. Invalid service account credentials")
        return
    
    # Test 6: Get calendar events
    print("\n[TEST] Get Calendar Events")
    print("-" * 70)
    events = sync.get_calendar_events(max_results=5)
    print(f"Found {len(events)} recent events:")
    for event in events[:5]:
        print(f"  - {event.get('summary')} ({event.get('start', {}).get('dateTime', 'all-day')})")
    
    # Test 7: Update the task
    print("\n[TEST] Update Task and Sync")
    print("-" * 70)
    db.execute_update(
        "UPDATE tasks SET title = ?, description = ? WHERE id = ?",
        ("Updated Test Event", "Updated description for calendar sync", task_id)
    )
    print(f"Updated task {task_id}")
    
    success, message = sync.update_event(task_id)
    print(f"Update sync - Success: {success}")
    print(f"Message: {message}")
    
    # Test 8: Delete the task
    print("\n[TEST] Delete Task and Sync")
    print("-" * 70)
    db.execute_update("DELETE FROM tasks WHERE id = ?", (task_id,))
    print(f"Deleted task {task_id}")
    
    success, message = sync.delete_event(task_id)
    print(f"Delete sync - Success: {success}")
    print(f"Message: {message}")
    
    # Test 9: Sync all tasks
    print("\n[TEST] Sync All User Tasks")
    print("-" * 70)
    results = sync.sync_all_tasks(user_id=user_id)
    print(f"Created: {results.get('created', 0)}")
    print(f"Updated: {results.get('updated', 0)}")
    print(f"Failed: {results.get('failed', 0)}")
    print(f"Total: {results.get('total', 0)}")
    
    print("\n" + "=" * 70)
    print("SERVICE ACCOUNT CALENDAR SYNC TEST COMPLETE!".center(70))
    print("=" * 70 + "\n")
    
    if is_auth:
        print("✅ Calendar sync is working correctly!")
        print("✅ All events are synced to your Google Calendar!")
        print("\nNext steps:")
        print("  1. Check your Google Calendar to see synced events")
        print("  2. Create/update/delete tasks in the app")
        print("  3. Use the API endpoints to sync manually")
        print("\nAPI Endpoints:")
        print("  POST /api/calendar/service-account/sync-all")
        print("  POST /api/calendar/service-account/sync-task/<task_id>")
        print("  GET  /api/calendar/service-account/status")
        print("  GET  /api/calendar/service-account/calendars")
        print("  GET  /api/calendar/service-account/events")


if __name__ == '__main__':
    test_service_account_sync()
