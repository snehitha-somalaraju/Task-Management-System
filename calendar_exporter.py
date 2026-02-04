"""
Calendar Exporter - Exports tasks to iCalendar format (.ics)
"""

import os
from datetime import datetime
from typing import List, Optional
from icalendar import Calendar, Event, vCalAddress, vText
from database import Database


class CalendarExporter:
    """
    Exports tasks to iCalendar format compatible with Google Calendar,
    Outlook, Apple Calendar, and other calendar applications.
    """
    
    def __init__(self, db: Database):
        """Initialize calendar exporter with database instance."""
        self.db = db
    
    # ==================== CALENDAR EXPORT ====================
    
    def export_tasks_to_ics(self, output_file: str = "tasks.ics", task_ids: List[int] = None) -> bool:
        """
        Export tasks to .ics file.
        
        Args:
            output_file: Output file path
            task_ids: Specific task IDs to export (None = all tasks)
        """
        try:
            # Create calendar
            cal = Calendar()
            cal.add('prodid', '-//Task Management System//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            cal.add('x-wr-calname', 'Task Management System')
            cal.add('x-wr-timezone', 'UTC')
            cal.add('x-wr-caldesc', 'Exported tasks from Task Management System')
            
            # Get tasks to export
            if task_ids:
                tasks = [self.db.get_task(tid) for tid in task_ids if self.db.get_task(tid)]
            else:
                tasks = self.db.get_all_tasks()
            
            # Add tasks as events
            for task in tasks:
                event = self._create_event(task)
                if event:
                    cal.add_component(event)
            
            # Write to file
            output_path = os.path.join(os.path.dirname(__file__), output_file)
            with open(output_path, 'wb') as f:
                f.write(cal.to_ical())
            
            print(f"✓ Exported {len(tasks)} tasks to '{output_file}'")
            return True
        
        except Exception as e:
            print(f"✗ Export failed: {e}")
            return False
    
    def export_undone_tasks(self, output_file: str = "tasks_undone.ics") -> bool:
        """Export all incomplete tasks."""
        tasks = self.db.get_all_tasks()
        undone_tasks = [t for t in tasks if t['status'] != 'done']
        task_ids = [t['id'] for t in undone_tasks]
        return self.export_tasks_to_ics(output_file, task_ids)
    
    def export_priority_tasks(self, priority: str, output_file: str = None) -> bool:
        """Export tasks by priority level."""
        if output_file is None:
            output_file = f"tasks_{priority}.ics"
        
        tasks = self.db.get_tasks_by_priority(priority)
        task_ids = [t['id'] for t in tasks]
        return self.export_tasks_to_ics(output_file, task_ids)
    
    def export_overdue_tasks(self, output_file: str = "tasks_overdue.ics") -> bool:
        """Export overdue tasks."""
        today = datetime.now().isoformat().split('T')[0]
        tasks = self.db.get_all_tasks()
        overdue_tasks = [
            t for t in tasks 
            if t['due_date'] and t['due_date'] < today and t['status'] != 'done'
        ]
        task_ids = [t['id'] for t in overdue_tasks]
        return self.export_tasks_to_ics(output_file, task_ids)
    
    # ==================== EVENT CREATION ====================
    
    def _create_event(self, task: dict) -> Optional[Event]:
        """Convert a task to an iCalendar event."""
        try:
            event = Event()
            
            # Summary (task title)
            event.add('summary', task['title'])
            
            # Description (task description + metadata)
            description = task['description'] if task['description'] else ""
            description += f"\n\nPriority: {task['priority']}"
            description += f"\nStatus: {task['status']}"
            
            if task['is_recurring']:
                description += "\nRecurring: Yes"
            
            event.add('description', vText(description))
            
            # UID (unique identifier)
            event.add('uid', f"task-{task['id']}@task-management-system")
            
            # Timestamps
            event.add('created', self._parse_datetime(task['created_at']))
            event.add('last-modified', self._parse_datetime(task['updated_at']))
            
            # Start and Due dates
            if task['due_date']:
                try:
                    due = datetime.fromisoformat(task['due_date'])
                    event.add('dtstart', due.date())
                    # End date is one day after due date (for all-day events)
                    event.add('dtend', (due + __import__('datetime').timedelta(days=1)).date())
                    event.add('due', due.date())
                except:
                    pass
            else:
                event.add('dtstart', self._parse_datetime(task['created_at']).date())
            
            # Priority mapping (1=high, 5=medium, 9=low)
            priority_map = {'high': 1, 'medium': 5, 'low': 9}
            event.add('priority', priority_map.get(task['priority'], 5))
            
            # Status mapping
            status_map = {
                'done': 'COMPLETED',
                'in_progress': 'IN-PROCESS',
                'blocked': 'CANCELLED',
                'not_started': 'NEEDS-ACTION'
            }
            event.add('status', status_map.get(task['status'], 'NEEDS-ACTION'))
            
            # Categories
            event.add('categories', [task['priority'].upper()])
            
            # Recurring rule if applicable
            if task['is_recurring'] and task['recurring_pattern_id']:
                pattern = self.db.get_recurring_pattern(task['recurring_pattern_id'])
                if pattern:
                    rrule = self._create_rrule(pattern)
                    if rrule:
                        event.add('rrule', rrule)
            
            return event
        
        except Exception as e:
            print(f"Warning: Could not create event for task {task['id']}: {e}")
            return None
    
    def _create_rrule(self, pattern: dict) -> Optional[dict]:
        """Create RRULE (recurrence rule) from recurring pattern."""
        try:
            rrule = {}
            
            # Frequency
            freq_map = {
                'daily': 'DAILY',
                'weekly': 'WEEKLY',
                'monthly': 'MONTHLY'
            }
            rrule['freq'] = freq_map.get(pattern['frequency'], 'DAILY')
            
            # Interval
            if pattern['interval'] and pattern['interval'] > 1:
                rrule['interval'] = pattern['interval']
            
            # End date
            if pattern['end_date']:
                try:
                    end = datetime.fromisoformat(pattern['end_date'])
                    rrule['until'] = end.date()
                except:
                    pass
            
            # Days of week for weekly
            if pattern['frequency'] == 'weekly' and pattern['days_of_week']:
                days = pattern['days_of_week']
                if isinstance(days, str):
                    # Convert day names to iCal format
                    day_map = {
                        'Monday': 'MO', 'Tuesday': 'TU', 'Wednesday': 'WE',
                        'Thursday': 'TH', 'Friday': 'FR', 'Saturday': 'SA', 'Sunday': 'SU'
                    }
                    day_list = [day_map.get(d.strip(), '') for d in days.split(',')]
                    rrule['byweekday'] = [d for d in day_list if d]
            
            return rrule if rrule else None
        
        except Exception as e:
            print(f"Warning: Could not create RRULE: {e}")
            return None
    
    def _parse_datetime(self, dt_string: str):
        """Parse datetime string to datetime object."""
        try:
            return datetime.fromisoformat(dt_string)
        except:
            return datetime.now()
    
    # ==================== CALENDAR IMPORT ====================
    
    def import_ics_file(self, file_path: str) -> int:
        """Import tasks from .ics file."""
        try:
            imported_count = 0
            
            with open(file_path, 'rb') as f:
                cal = Calendar.from_ical(f.read())
            
            for component in cal.walk():
                if component.name == "VEVENT":
                    # Extract task details
                    title = component.get('summary', 'Imported Task')
                    description = component.get('description', '')
                    
                    # Parse priority
                    priority_value = component.get('priority', 5)
                    priority_map = {1: 'high', 5: 'medium', 9: 'low'}
                    priority = priority_map.get(int(priority_value), 'medium')
                    
                    # Parse due date
                    due = component.get('due', component.get('dtstart'))
                    due_date = str(due.date()) if due else None
                    
                    # Create task
                    task_id = self.db.create_task(title, description, priority, due_date)
                    imported_count += 1
            
            print(f"✓ Imported {imported_count} tasks from '{file_path}'")
            return imported_count
        
        except Exception as e:
            print(f"✗ Import failed: {e}")
            return 0
    
    # ==================== UTILITY ====================
    
    def list_exported_files(self) -> List[str]:
        """List all exported .ics files in project directory."""
        project_dir = os.path.dirname(__file__)
        ics_files = [f for f in os.listdir(project_dir) if f.endswith('.ics')]
        return ics_files
    
    def export_summary(self, output_file: str = "tasks_summary.ics") -> bool:
        """Export a summary with counts and recent activity."""
        try:
            from analytics import Analytics
            analytics = Analytics(self.db)
            
            cal = Calendar()
            cal.add('prodid', '-//Task Management System//Summary//EN')
            cal.add('version', '2.0')
            
            # Create event with summary stats
            event = Event()
            dashboard = analytics.get_productivity_dashboard()
            
            summary = "Task Management Summary\n"
            summary += f"Total Tasks: {dashboard['completion_rate']['total_tasks']}\n"
            summary += f"Completed: {dashboard['completion_rate']['completed_tasks']}\n"
            summary += f"Completion Rate: {dashboard['completion_rate']['completion_rate']}%\n"
            summary += f"Overdue: {dashboard['overdue_count']}\n"
            summary += f"Blocked: {dashboard['blocked_count']}"
            
            event.add('summary', 'Task Summary')
            event.add('description', summary)
            event.add('dtstart', datetime.now().date())
            event.add('uid', 'summary@task-management-system')
            
            cal.add_component(event)
            
            output_path = os.path.join(os.path.dirname(__file__), output_file)
            with open(output_path, 'wb') as f:
                f.write(cal.to_ical())
            
            print(f"✓ Summary exported to '{output_file}'")
            return True
        
        except Exception as e:
            print(f"✗ Summary export failed: {e}")
            return False
