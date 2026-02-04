"""
Google Calendar Sync - Real-time synchronization with Google Calendar
Enables one-time authentication and automatic updates without manual ICS downloads
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2 import credentials as oauth_credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from database import Database


class GoogleCalendarSync:
    """
    Synchronizes tasks with Google Calendar.
    - One-time authentication setup
    - Automatic event creation/update/deletion
    - Real-time sync on task changes
    """
    
    # Google Calendar API scope
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, db: Database, credentials_file: str = "google_credentials.json", 
                 token_file: str = "token.pickle"):
        """
        Initialize Google Calendar sync.
        
        Args:
            db: Database instance
            credentials_file: Path to Google OAuth 2.0 credentials JSON
            token_file: Path to store authentication token
        """
        self.db = db
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.calendar_id = 'primary'  # Use primary calendar
        self.task_event_map = {}  # Maps task_id to google event_id
        self.mapping_file = "task_event_mapping.json"
        
        self._load_mapping()
    
    # ==================== AUTHENTICATION ====================
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.
        First time: Opens browser for user to authorize
        Subsequent times: Uses stored token automatically
        
        Returns:
            bool: True if authentication successful
        """
        try:
            creds = None
            
            # Load existing token if available
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh token if expired or get new one
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(requests.Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        print("✗ Error: Google credentials file not found!")
                        print("  Follow SETUP.md to get credentials from Google Cloud Console")
                        return False
                    
                    # Launch browser for user authorization
                    # Use port 5000 to match redirect_uri configured in Google Cloud Console
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    # run_local_server with specific port matching our OAuth config
                    creds = flow.run_local_server(
                        port=5000,
                        open_browser=True,
                        authorization_prompt_message='Please visit this URL in your browser to authorize:\n{url}\n'
                    )
                
                # Save token for future use
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            print("✓ Successfully authenticated with Google Calendar")
            return True
        
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== TASK-CALENDAR MAPPING ====================
    
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
    
    def _create_event_body(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert task to Google Calendar event format.
        
        Args:
            task: Task dictionary from database
            
        Returns:
            dict: Event body for Google Calendar API
        """
        event = {
            'summary': task['title'],
            'description': self._build_description(task),
            'colorId': self._get_color_by_priority(task['priority']),
        }
        
        # Set dates
        if task['due_date']:
            try:
                due = datetime.fromisoformat(task['due_date'])
                event['start'] = {'date': due.strftime('%Y-%m-%d')}
                event['end'] = {'date': (due + timedelta(days=1)).strftime('%Y-%m-%d')}
            except:
                pass
        
        # Add custom property to identify as task
        event['extendedProperties'] = {
            'private': {
                'task_id': str(task['id']),
                'priority': task['priority'],
                'status': task['status']
            }
        }
        
        return event
    
    def _build_description(self, task: Dict[str, Any]) -> str:
        """Build event description from task details."""
        desc = f"{task['description'] or 'No description'}\n\n"
        desc += f"Status: {task['status']}\n"
        desc += f"Priority: {task['priority'].upper()}\n"
        desc += f"Task ID: {task['id']}\n"
        
        if task['time_spent']:
            desc += f"Time Spent: {task['time_spent']} hours\n"
        
        if task['is_recurring']:
            desc += f"Recurring: Yes\n"
        
        return desc
    
    def _get_color_by_priority(self, priority: str) -> str:
        """Map task priority to Google Calendar color ID."""
        color_map = {
            'high': '11',    # Red
            'medium': '5',   # Yellow
            'low': '2'       # Blue
        }
        return color_map.get(priority, '5')
    
    # ==================== CREATE OPERATIONS ====================
    
    def create_event(self, task_id: int) -> bool:
        """
        Create a Google Calendar event for a task.
        
        Args:
            task_id: Task ID to create event for
            
        Returns:
            bool: True if successful
        """
        if not self.service:
            print("✗ Not authenticated. Call authenticate() first.")
            return False
        
        try:
            task = self.db.get_task(task_id)
            if not task:
                print(f"✗ Task {task_id} not found")
                return False
            
            # Skip if already created
            if str(task_id) in self.task_event_map:
                print(f"ℹ Task {task_id} already synced. Use update_event() instead.")
                return False
            
            event_body = self._create_event_body(task)
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body
            ).execute()
            
            # Store mapping
            self.task_event_map[str(task_id)] = event['id']
            self._save_mapping()
            
            print(f"✓ Created Google Calendar event for task {task_id}")
            return True
        
        except HttpError as e:
            print(f"✗ Failed to create event: {e}")
            return False
    
    def create_all_events(self) -> int:
        """
        Create Google Calendar events for all unsynced tasks.
        
        Returns:
            int: Number of events created
        """
        if not self.service:
            print("✗ Not authenticated. Call authenticate() first.")
            return 0
        
        tasks = self.db.get_all_tasks()
        created = 0
        
        for task in tasks:
            if str(task['id']) not in self.task_event_map:
                if self.create_event(task['id']):
                    created += 1
        
        print(f"✓ Created {created} Google Calendar events")
        return created
    
    # ==================== UPDATE OPERATIONS ====================
    
    def update_event(self, task_id: int) -> bool:
        """
        Update Google Calendar event when task is modified.
        
        Args:
            task_id: Task ID to update event for
            
        Returns:
            bool: True if successful
        """
        if not self.service:
            print("✗ Not authenticated. Call authenticate() first.")
            return False
        
        try:
            # Get event ID from mapping
            event_id = self.task_event_map.get(str(task_id))
            if not event_id:
                print(f"ℹ Task {task_id} not synced. Creating new event...")
                return self.create_event(task_id)
            
            task = self.db.get_task(task_id)
            if not task:
                print(f"✗ Task {task_id} not found")
                return False
            
            event_body = self._create_event_body(task)
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event_body
            ).execute()
            
            print(f"✓ Updated Google Calendar event for task {task_id}")
            return True
        
        except HttpError as e:
            print(f"✗ Failed to update event: {e}")
            return False
    
    # ==================== DELETE OPERATIONS ====================
    
    def delete_event(self, task_id: int) -> bool:
        """
        Delete Google Calendar event when task is deleted.
        
        Args:
            task_id: Task ID to delete event for
            
        Returns:
            bool: True if successful
        """
        if not self.service:
            print("✗ Not authenticated. Call authenticate() first.")
            return False
        
        try:
            event_id = self.task_event_map.get(str(task_id))
            if not event_id:
                print(f"ℹ Task {task_id} not found in calendar mapping")
                return True
            
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Remove from mapping
            del self.task_event_map[str(task_id)]
            self._save_mapping()
            
            print(f"✓ Deleted Google Calendar event for task {task_id}")
            return True
        
        except HttpError as e:
            print(f"✗ Failed to delete event: {e}")
            return False
    
    # ==================== SYNC OPERATIONS ====================
    
    def sync_all(self) -> Dict[str, int]:
        """
        Full synchronization: Create, update, and delete events.
        
        Returns:
            dict: Counts of created, updated, and deleted events
        """
        if not self.service:
            print("✗ Not authenticated. Call authenticate() first.")
            return {'created': 0, 'updated': 0, 'deleted': 0}
        
        results = {'created': 0, 'updated': 0, 'deleted': 0}
        tasks = self.db.get_all_tasks()
        
        # Create/update events
        for task in tasks:
            task_id = str(task['id'])
            if task_id not in self.task_event_map:
                if self.create_event(task['id']):
                    results['created'] += 1
            else:
                if self.update_event(task['id']):
                    results['updated'] += 1
        
        # Delete events for removed tasks
        tasks_in_db = {str(t['id']) for t in tasks}
        to_delete = [tid for tid in self.task_event_map.keys() if tid not in tasks_in_db]
        for task_id in to_delete:
            if self.delete_event(int(task_id)):
                results['deleted'] += 1
        
        print(f"✓ Sync complete: {results['created']} created, "
              f"{results['updated']} updated, {results['deleted']} deleted")
        return results
    
    def get_synced_events(self) -> List[Dict[str, Any]]:
        """
        Retrieve all synced events from Google Calendar.
        
        Returns:
            list: Events from Google Calendar
        """
        if not self.service:
            print("✗ Not authenticated. Call authenticate() first.")
            return []
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                q='task_id',  # Filter for our custom property
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        
        except HttpError as e:
            print(f"✗ Failed to retrieve events: {e}")
            return []
