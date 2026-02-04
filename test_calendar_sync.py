#!/usr/bin/env python3
"""
Complete Google Calendar Sync Testing Script
Tests all calendar synchronization features
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_success(text):
    print(f"✓ {text}")

def print_error(text):
    print(f"✗ {text}")

def print_info(text):
    print(f"→ {text}")

# Test 1: Check if Flask is running
print_header("TEST 1: Flask Server Status")
try:
    response = requests.get(f"{BASE_URL}/api/health", timeout=5)
    if response.status_code == 200:
        print_success("Flask server is running")
    else:
        print_error(f"Flask returned status code {response.status_code}")
except Exception as e:
    print_error(f"Cannot connect to Flask: {e}")
    exit(1)

# Test 2: Check calendar sync status
print_header("TEST 2: Google Calendar Sync Status")
try:
    response = requests.get(f"{BASE_URL}/api/calendar/status", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print_info(f"Authentication Status: {data.get('is_authenticated', False)}")
        print_info(f"Synced Tasks: {data.get('synced_tasks', 0)}")
        print_info(f"Last Sync: {data.get('last_sync', 'Never')}")
        print_success("Calendar sync status retrieved")
    else:
        print_error(f"Failed to get status: {response.status_code}")
except Exception as e:
    print_error(f"Error checking status: {e}")

# Test 3: Authenticate with Google Calendar
print_header("TEST 3: Google Calendar Authentication")
print_info("Attempting to authenticate...")
try:
    response = requests.post(f"{BASE_URL}/api/calendar/authenticate", timeout=10)
    if response.status_code == 200:
        data = response.json()
        if 'message' in data:
            print_success(data['message'])
        elif 'auth_url' in data:
            print_info(f"Please open this URL to authenticate: {data['auth_url']}")
            print_info("Waiting for authentication...")
            time.sleep(5)
        else:
            print_info(f"Response: {data}")
    else:
        print_error(f"Authentication failed: {response.status_code} - {response.text}")
except Exception as e:
    print_error(f"Authentication error: {e}")

# Test 4: Create a test task
print_header("TEST 4: Creating Test Task")
task_data = {
    "title": f"CALENDAR TEST - {datetime.now().strftime('%H:%M:%S')}",
    "description": "This is a test task for Google Calendar sync",
    "priority": "high",
    "status": "pending"
}

task_id = None
try:
    response = requests.post(
        f"{BASE_URL}/api/tasks",
        json=task_data,
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    if response.status_code in [200, 201]:
        data = response.json()
        task_id = data.get('id')
        print_success(f"Task created with ID: {task_id}")
        print_info(f"Title: {data.get('title')}")
        print_info(f"Priority: {data.get('priority')}")
    else:
        print_error(f"Failed to create task: {response.status_code}")
except Exception as e:
    print_error(f"Error creating task: {e}")

# Test 5: Sync task to Google Calendar
if task_id:
    print_header("TEST 5: Syncing Task to Google Calendar")
    try:
        response = requests.post(
            f"{BASE_URL}/api/calendar/sync/create/{task_id}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Task synced to Google Calendar")
            print_info(f"Response: {data.get('message', str(data))}")
        else:
            print_error(f"Sync failed: {response.status_code} - {response.text}")
    except Exception as e:
        print_error(f"Sync error: {e}")

    # Test 6: Update the task
    print_header("TEST 6: Updating Task")
    update_data = {
        "title": f"UPDATED - {datetime.now().strftime('%H:%M:%S')}",
        "status": "in_progress",
        "priority": "medium"
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json=update_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Task updated")
            print_info(f"New Title: {data.get('title')}")
            print_info(f"New Status: {data.get('status')}")
        else:
            print_error(f"Failed to update task: {response.status_code}")
    except Exception as e:
        print_error(f"Update error: {e}")

    # Test 7: Sync the update to Google Calendar
    print_header("TEST 7: Syncing Update to Google Calendar")
    try:
        response = requests.post(
            f"{BASE_URL}/api/calendar/sync/update/{task_id}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Update synced to Google Calendar")
            print_info(f"Response: {data.get('message', str(data))}")
        else:
            print_error(f"Update sync failed: {response.status_code}")
    except Exception as e:
        print_error(f"Update sync error: {e}")

    # Test 8: Delete the task
    print_header("TEST 8: Deleting Test Task")
    try:
        response = requests.delete(
            f"{BASE_URL}/api/tasks/{task_id}",
            timeout=5
        )
        if response.status_code == 200:
            print_success(f"Task deleted from database")
        else:
            print_error(f"Failed to delete task: {response.status_code}")
    except Exception as e:
        print_error(f"Delete error: {e}")

    # Test 9: Remove from Google Calendar
    print_header("TEST 9: Removing Task from Google Calendar")
    try:
        response = requests.post(
            f"{BASE_URL}/api/calendar/sync/delete/{task_id}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Task removed from Google Calendar")
            print_info(f"Response: {data.get('message', str(data))}")
        else:
            print_error(f"Deletion sync failed: {response.status_code}")
    except Exception as e:
        print_error(f"Deletion sync error: {e}")

# Test 10: Full sync of all tasks
print_header("TEST 10: Full Sync of All Tasks")
try:
    response = requests.post(
        f"{BASE_URL}/api/calendar/sync/all",
        timeout=30
    )
    if response.status_code == 200:
        data = response.json()
        print_success("Full sync completed")
        print_info(f"Created: {data.get('created', 0)}")
        print_info(f"Updated: {data.get('updated', 0)}")
        print_info(f"Deleted: {data.get('deleted', 0)}")
        print_info(f"Total: {data.get('total_synced', 0)}")
    else:
        print_error(f"Full sync failed: {response.status_code}")
except Exception as e:
    print_error(f"Full sync error: {e}")

# Final status
print_header("FINAL STATUS")
try:
    response = requests.get(f"{BASE_URL}/api/calendar/status", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print_info(f"Authentication: {'✓ Yes' if data.get('is_authenticated') else '✗ No'}")
        print_info(f"Synced Tasks: {data.get('synced_tasks', 0)}")
        print_success("All tests completed!")
    else:
        print_error("Could not retrieve final status")
except Exception as e:
    print_error(f"Error: {e}")

print("\n" + "="*70)
print("  Open Google Calendar to verify events: https://calendar.google.com")
print("="*70 + "\n")
