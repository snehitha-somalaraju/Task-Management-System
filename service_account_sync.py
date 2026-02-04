"""
Service Account Calendar Sync
Syncs tasks with Google Calendar using Service Account authentication
No OAuth redirect needed - fully automated!
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from database import Database


class ServiceAccountCalendarSync:
    """
    Syncs tasks with Google Calendar using Service Account credentials
    Benefits:
    - No OAuth redirect flow needed
    - Fully automated
    - More reliable
    - Perfect for background syncing
    """
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, db: Database, service_account_file: str = 'task-management-system-485303-73e5b29099d4.json'):
        """
        Initialize Service Account Calendar Sync
        
        Args:
            db: Database instance
            service_account_file: Path to service account JSON key file
        """
        self.db = db
        self.service_account_file = service_account_file
        self.service = None
        self.calendar_id = 'primary'  # Use user's primary calendar
        self.task_event_map = {}  # Maps task_id to calendar event_id
        
        # Try to authenticate
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API using Service Account
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            if not os.path.exists(self.service_account_file):
                print(f"[!] Service account file not found: {self.service_account_file}")
                return False
            
            # Load credentials from service account JSON file
            with open(self.service_account_file, 'r') as f:
                service_account_info = json.load(f)
            
            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES
            )
            
            # Build the Calendar service
            self.service = build('calendar', 'v3', credentials=credentials)
            
            print("[OK] Authenticated with Google Calendar (Service Account)")
            print(f"[OK] Service Account Email: {service_account_info.get('client_email')}")
            
            # Test the connection
            try:
                calendars = self.service.calendarList().list().execute()
                print(f"[OK] Calendar access verified - {len(calendars.get('items', []))} calendars available")
            except Exception as e:
                print(f"[!] Warning: Could not access calendars - {str(e)}")
                print("[!] Make sure you've shared your calendar with the service account!")
                return False
            
            return True
        
        except Exception as e:
            print(f"[!] Authentication failed: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if authenticated with Google Calendar"""
        return self.service is not None
    
    # ==================== TASK TO EVENT CONVERSION ====================
    
    def task_to_event(self, task: Dict) -> Dict:
        """
        Convert a task to a Google Calendar event
        
        Args:
            task: Task dictionary from database
        
        Returns:
            Google Calendar event dictionary
        """
        title = task.get('title', 'Untitled Task')
        description = task.get('description', '')
        priority = task.get('priority', 'medium')
        status = task.get('status', 'not_started')
        due_date = task.get('due_date')
        
        # Build event title with priority indicator
        priority_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }
        emoji = priority_emoji.get(priority, '')
        event_title = f"{emoji} {title}"
        
        # Build description with task details
        event_description = f"""Task Details:
Priority: {priority}
Status: {status}
Created: {task.get('created_at', '')}

{description}"""
        
        # Build event time
        if due_date:
            try:
                # Parse due_date (format: YYYY-MM-DD or ISO datetime)
                if 'T' in str(due_date):
                    # ISO format with time
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                else:
                    # Date only
                    due_dt = datetime.fromisoformat(due_date)
                
                start_time = due_dt
                end_time = due_dt + timedelta(hours=1)
            except:
                # Fallback: use today as start
                start_time = datetime.now()
                end_time = start_time + timedelta(hours=1)
        else:
            # No due date: use today
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=1)
        
        # Build event color based on priority
        color_id = {
            'high': '11',      # Red
            'medium': '5',     # Yellow
            'low': '2'         # Blue
        }.get(priority, '0')
        
        event = {
            'summary': event_title,
            'description': event_description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC'
            },
            'colorId': color_id,
            'transparency': 'opaque' if status == 'done' else 'transparent',
            'extendedProperties': {
                'private': {
                    'task_id': str(task.get('id', ''))
                }
            }
        }
        
        return event
    
    # ==================== CREATE EVENT ====================
    
    def create_event(self, task_id: int) -> Tuple[bool, str]:
        """
        Create a calendar event for a task
        
        Args:
            task_id: Task ID to create event for
        
        Returns:
            (success: bool, message: str)
        """
        if not self.is_authenticated():
            return False, "Not authenticated with Google Calendar"
        
        try:
            # Get task from database
            task = self.db.get_task(task_id)
            if not task:
                return False, f"Task {task_id} not found"
            
            # Convert task to event
            event = self.task_to_event(task)
            
            # Create event in Google Calendar
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            event_id = created_event.get('id')
            
            # Store mapping in database (optional: create a new table for this)
            # For now, store in memory
            self.task_event_map[task_id] = event_id
            
            print(f"[OK] Created calendar event for task {task_id}: {event_id}")
            return True, f"Event created: {event_id}"
        
        except Exception as e:
            print(f"[!] Error creating calendar event: {str(e)}")
            return False, f"Failed to create event: {str(e)}"
    
    # ==================== UPDATE EVENT ====================
    
    def update_event(self, task_id: int) -> Tuple[bool, str]:
        """
        Update calendar event for a task
        
        Args:
            task_id: Task ID to update event for
        
        Returns:
            (success: bool, message: str)
        """
        if not self.is_authenticated():
            return False, "Not authenticated with Google Calendar"
        
        try:
            # Get the event ID
            event_id = self.task_event_map.get(task_id)
            if not event_id:
                # Event doesn't exist, create it
                return self.create_event(task_id)
            
            # Get updated task
            task = self.db.get_task(task_id)
            if not task:
                return False, f"Task {task_id} not found"
            
            # Convert to event
            event = self.task_to_event(task)
            
            # Update event in Google Calendar
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            print(f"[OK] Updated calendar event for task {task_id}")
            return True, f"Event updated: {event_id}"
        
        except Exception as e:
            print(f"[!] Error updating calendar event: {str(e)}")
            return False, f"Failed to update event: {str(e)}"
    
    # ==================== DELETE EVENT ====================
    
    def delete_event(self, task_id: int) -> Tuple[bool, str]:
        """
        Delete calendar event for a task
        
        Args:
            task_id: Task ID to delete event for
        
        Returns:
            (success: bool, message: str)
        """
        if not self.is_authenticated():
            return False, "Not authenticated with Google Calendar"
        
        try:
            # Get the event ID
            event_id = self.task_event_map.get(task_id)
            if not event_id:
                return False, f"No calendar event found for task {task_id}"
            
            # Delete event from Google Calendar
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Remove from mapping
            del self.task_event_map[task_id]
            
            print(f"[OK] Deleted calendar event for task {task_id}")
            return True, "Event deleted"
        
        except Exception as e:
            print(f"[!] Error deleting calendar event: {str(e)}")
            return False, f"Failed to delete event: {str(e)}"
    
    # ==================== SYNC OPERATIONS ====================
    
    def sync_task(self, task_id: int) -> Tuple[bool, str]:
        """
        Sync a single task with calendar (create or update)
        
        Args:
            task_id: Task ID to sync
        
        Returns:
            (success: bool, message: str)
        """
        if not self.is_authenticated():
            return False, "Not authenticated with Google Calendar"
        
        # Check if event already exists
        if task_id in self.task_event_map:
            return self.update_event(task_id)
        else:
            return self.create_event(task_id)
    
    def sync_all_tasks(self, user_id: int = None) -> Dict:
        """
        Sync all tasks with calendar
        
        Args:
            user_id: Optional user ID to sync only that user's tasks
        
        Returns:
            Dictionary with sync results {created, updated, failed}
        """
        if not self.is_authenticated():
            return {'created': 0, 'updated': 0, 'failed': 0, 'error': 'Not authenticated'}
        
        try:
            # Get all tasks
            query = "SELECT id FROM tasks"
            if user_id:
                query += f" WHERE user_id = {user_id}"
            
            results = self.db.execute_query(query)
            task_ids = [dict(row)['id'] for row in results]
            
            created = 0
            updated = 0
            failed = 0
            
            print(f"\n[*] Syncing {len(task_ids)} tasks with calendar...")
            
            for task_id in task_ids:
                success, message = self.sync_task(task_id)
                if success:
                    if task_id in self.task_event_map:
                        updated += 1
                    else:
                        created += 1
                else:
                    failed += 1
            
            print(f"[OK] Sync complete: {created} created, {updated} updated, {failed} failed")
            
            return {
                'created': created,
                'updated': updated,
                'failed': failed,
                'total': len(task_ids)
            }
        
        except Exception as e:
            print(f"[!] Error syncing tasks: {str(e)}")
            return {'created': 0, 'updated': 0, 'failed': -1, 'error': str(e)}
    
    def get_sync_status(self) -> Dict:
        """
        Get current sync status
        
        Returns:
            Dictionary with sync status
        """
        return {
            'authenticated': self.is_authenticated(),
            'synced_tasks': len(self.task_event_map),
            'task_event_map': self.task_event_map,
            'service_status': 'connected' if self.is_authenticated() else 'disconnected'
        }
    
    # ==================== CALENDAR LISTING ====================
    
    def list_calendars(self) -> List[Dict]:
        """
        List all available calendars
        
        Returns:
            List of calendar dictionaries
        """
        if not self.is_authenticated():
            return []
        
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            result = []
            for cal in calendars:
                result.append({
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'primary': cal.get('primary', False),
                    'timezone': cal.get('timeZone')
                })
            
            return result
        
        except Exception as e:
            print(f"[!] Error listing calendars: {str(e)}")
            return []
    
    def get_calendar_events(self, max_results: int = 10) -> List[Dict]:
        """
        Get recent events from calendar
        
        Args:
            max_results: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        if not self.is_authenticated():
            return []
        
        try:
            events = self.service.events().list(
                calendarId=self.calendar_id,
                maxResults=max_results,
                orderBy='startTime',
                singleEvents=True
            ).execute()
            
            return events.get('items', [])
        
        except Exception as e:
            print(f"[!] Error getting calendar events: {str(e)}")
            return []
