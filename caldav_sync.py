"""
CalDAV Sync - Alternative calendar synchronization using CalDAV protocol
Works with Google Calendar, Outlook, Apple Calendar, Nextcloud, etc.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from icalendar import Calendar, Event, vCalAddress, vText

# Note: caldav library is optional
try:
    import caldav
    CALDAV_AVAILABLE = True
except ImportError:
    CALDAV_AVAILABLE = False
    print("⚠ CalDAV library not installed. Install with: pip install caldav")

from database import Database


class CalDAVSync:
    """
    Synchronizes tasks using CalDAV protocol.
    Supports: Google Calendar, Outlook, Apple Calendar, Nextcloud, etc.
    
    This is an alternative to Google Calendar API that works with any CalDAV server.
    """
    
    def __init__(self, db: Database, config_file: str = "caldav_config.json"):
        """
        Initialize CalDAV sync.
        
        Args:
            db: Database instance
            config_file: Path to CalDAV configuration file
        """
        if not CALDAV_AVAILABLE:
            raise ImportError("caldav library not installed. Run: pip install caldav")
        
        self.db = db
        self.config_file = config_file
        self.client = None
        self.calendar = None
        self.task_event_map = {}
        self.mapping_file = "caldav_event_mapping.json"
        
        self._load_config()
        self._load_mapping()
    
    # ==================== CONFIGURATION ====================
    
    def _load_config(self) -> Dict[str, Any]:
        """Load CalDAV configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self, url: str, username: str, password: str, calendar_name: str) -> bool:
        """
        Save CalDAV connection configuration.
        
        Args:
            url: CalDAV server URL (e.g., https://caldav.google.com/calendar/dav/)
            username: CalDAV username
            password: CalDAV password or app-specific password
            calendar_name: Calendar name to use
            
        Returns:
            bool: True if successful
        """
        try:
            config = {
                'url': url,
                'username': username,
                'password': password,  # Consider encryption in production!
                'calendar_name': calendar_name,
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✓ Saved CalDAV configuration")
            return True
        
        except Exception as e:
            print(f"✗ Failed to save configuration: {e}")
            return False
    
    def _load_mapping(self):
        """Load task-to-event mapping from file."""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r') as f:
                    self.task_event_map = json.load(f)
            except:
                self.task_event_map = {}
    
    def _save_mapping(self):
        """Save task-to-event mapping to file."""
        with open(self.mapping_file, 'w') as f:
            json.dump(self.task_event_map, f, indent=2)
    
    # ==================== CONNECTION ====================
    
    def connect(self) -> bool:
        """
        Connect to CalDAV server using saved configuration.
        
        Returns:
            bool: True if successful
        """
        try:
            config = self._load_config()
            
            if not all(k in config for k in ['url', 'username', 'password', 'calendar_name']):
                print("✗ Incomplete CalDAV configuration. Use save_config() first.")
                return False
            
            # Connect to CalDAV server
            self.client = caldav.DAVClient(
                url=config['url'],
                username=config['username'],
                password=config['password']
            )
            
            # Get calendar
            principal = self.client.principal()
            calendars = principal.calendars()
            
            # Find the specified calendar
            for cal in calendars:
                if config['calendar_name'] in cal.name:
                    self.calendar = cal
                    break
            
            if not self.calendar:
                print(f"✗ Calendar '{config['calendar_name']}' not found")
                return False
            
            print(f"✓ Connected to CalDAV server: {config['calendar_name']}")
            return True
        
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    # ==================== EVENT OPERATIONS ====================
    
    def _create_event_ical(self, task: Dict[str, Any]) -> str:
        """
        Convert task to iCalendar format for CalDAV.
        
        Args:
            task: Task dictionary from database
            
        Returns:
            str: iCalendar format string
        """
        cal = Calendar()
        cal.add('prodid', '-//Task Management System//EN')
        cal.add('version', '2.0')
        
        event = Event()
        event.add('summary', task['title'])
        
        # Description
        description = f"{task['description'] or 'No description'}\n\n"
        description += f"Status: {task['status']}\n"
        description += f"Priority: {task['priority'].upper()}\n"
        description += f"Task ID: {task['id']}\n"
        
        if task['time_spent']:
            description += f"Time Spent: {task['time_spent']} hours\n"
        
        if task['is_recurring']:
            description += f"Recurring: Yes\n"
        
        event.add('description', vText(description))
        
        # UID
        event.add('uid', f"task-{task['id']}@task-management-system")
        
        # Timestamps
        event.add('created', datetime.fromisoformat(task['created_at']))
        event.add('last-modified', datetime.fromisoformat(task['updated_at']))
        
        # Dates
        if task['due_date']:
            try:
                due = datetime.fromisoformat(task['due_date'])
                event.add('dtstart', due.date())
                event.add('dtend', (due + timedelta(days=1)).date())
            except:
                pass
        
        # Priority
        priority_map = {'high': 1, 'medium': 5, 'low': 9}
        event.add('priority', priority_map.get(task['priority'], 5))
        
        # Status
        status_map = {
            'done': 'COMPLETED',
            'in_progress': 'IN-PROCESS',
            'blocked': 'CANCELLED',
            'not_started': 'NEEDS-ACTION'
        }
        event.add('status', status_map.get(task['status'], 'NEEDS-ACTION'))
        
        # Categories
        event.add('categories', [task['priority'].upper()])
        
        cal.add_component(event)
        return cal.to_ical().decode('utf-8')
    
    def create_event(self, task_id: int) -> bool:
        """Create a CalDAV event for a task."""
        if not self.calendar:
            print("✗ Not connected to CalDAV server. Call connect() first.")
            return False
        
        try:
            task = self.db.get_task(task_id)
            if not task:
                print(f"✗ Task {task_id} not found")
                return False
            
            if str(task_id) in self.task_event_map:
                print(f"ℹ Task {task_id} already synced")
                return False
            
            ical_data = self._create_event_ical(task)
            event = self.calendar.save_event(ical_data)
            
            self.task_event_map[str(task_id)] = event.url
            self._save_mapping()
            
            print(f"✓ Created CalDAV event for task {task_id}")
            return True
        
        except Exception as e:
            print(f"✗ Failed to create event: {e}")
            return False
    
    def create_all_events(self) -> int:
        """Create CalDAV events for all unsynced tasks."""
        if not self.calendar:
            print("✗ Not connected to CalDAV server. Call connect() first.")
            return 0
        
        tasks = self.db.get_all_tasks()
        created = 0
        
        for task in tasks:
            if str(task['id']) not in self.task_event_map:
                if self.create_event(task['id']):
                    created += 1
        
        print(f"✓ Created {created} CalDAV events")
        return created
    
    def update_event(self, task_id: int) -> bool:
        """Update CalDAV event when task is modified."""
        if not self.calendar:
            print("✗ Not connected to CalDAV server. Call connect() first.")
            return False
        
        try:
            event_url = self.task_event_map.get(str(task_id))
            if not event_url:
                print(f"ℹ Task {task_id} not synced. Creating new event...")
                return self.create_event(task_id)
            
            task = self.db.get_task(task_id)
            if not task:
                print(f"✗ Task {task_id} not found")
                return False
            
            ical_data = self._create_event_ical(task)
            event = caldav.Event(self.calendar, url=event_url, data=ical_data)
            event.save()
            
            print(f"✓ Updated CalDAV event for task {task_id}")
            return True
        
        except Exception as e:
            print(f"✗ Failed to update event: {e}")
            return False
    
    def delete_event(self, task_id: int) -> bool:
        """Delete CalDAV event when task is deleted."""
        if not self.calendar:
            print("✗ Not connected to CalDAV server. Call connect() first.")
            return False
        
        try:
            event_url = self.task_event_map.get(str(task_id))
            if not event_url:
                print(f"ℹ Task {task_id} not found in mapping")
                return True
            
            event = caldav.Event(self.calendar, url=event_url)
            event.delete()
            
            del self.task_event_map[str(task_id)]
            self._save_mapping()
            
            print(f"✓ Deleted CalDAV event for task {task_id}")
            return True
        
        except Exception as e:
            print(f"✗ Failed to delete event: {e}")
            return False
    
    def sync_all(self) -> Dict[str, int]:
        """Full synchronization with CalDAV server."""
        if not self.calendar:
            print("✗ Not connected to CalDAV server. Call connect() first.")
            return {'created': 0, 'updated': 0, 'deleted': 0}
        
        results = {'created': 0, 'updated': 0, 'deleted': 0}
        tasks = self.db.get_all_tasks()
        
        for task in tasks:
            task_id = str(task['id'])
            if task_id not in self.task_event_map:
                if self.create_event(task['id']):
                    results['created'] += 1
            else:
                if self.update_event(task['id']):
                    results['updated'] += 1
        
        print(f"✓ CalDAV sync complete: {results['created']} created, "
              f"{results['updated']} updated, {results['deleted']} deleted")
        return results


# ==================== CALDAV CONFIGURATION HELPERS ====================

def get_caldav_urls():
    """Return common CalDAV server URLs."""
    return {
        'google': 'https://caldav.google.com/calendar/dav/',
        'outlook': 'https://outlook.office365.com/calendar/dav/',
        'apple': 'https://caldav.icloud.com/',
        'nextcloud': 'https://your-nextcloud-instance.com/remote.php/dav/',
    }
