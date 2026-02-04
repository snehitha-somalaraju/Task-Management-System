"""
Time Tracker Module - Handles time logging and duration tracking
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from database import Database


class TimeTracker:
    """
    Manages time tracking for tasks including starting, stopping,
    and analyzing time spent on various tasks.
    """
    
    def __init__(self, db: Database):
        """Initialize time tracker with database instance."""
        self.db = db
    
    # ==================== TIME LOGGING ====================
    
    def start_timer(self, task_id: int) -> int:
        """Start timer for a task."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return -1
        
        # Check if already running
        active = self.db.get_active_time_log(task_id)
        if active:
            print(f"✗ Timer already running for task '{task['title']}'")
            return active['id']
        
        time_log_id = self.db.start_time_log(task_id)
        print(f"✓ Timer started for task '{task['title']}' (Log ID: {time_log_id})")
        return time_log_id
    
    def stop_timer(self, task_id: int, notes: str = None) -> bool:
        """Stop timer for a task."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return False
        
        # Find active time log
        active = self.db.get_active_time_log(task_id)
        if not active:
            print(f"✗ No active timer for task '{task['title']}'")
            return False
        
        # Calculate duration
        start_dt = datetime.fromisoformat(active['start_time'])
        end_dt = datetime.now()
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        # End the log
        self.db.end_time_log(active['id'], notes=notes)
        print(f"✓ Timer stopped for task '{task['title']}' ({duration_minutes} minutes)")
        
        return True
    
    def pause_timer(self, task_id: int, notes: str = None) -> bool:
        """Pause timer (ends current session, can start new one later)."""
        return self.stop_timer(task_id, notes)
    
    def get_active_timers(self) -> List[Dict[str, Any]]:
        """Get all currently active timers."""
        query = """
            SELECT tl.*, t.title, t.priority, t.status
            FROM time_logs tl
            JOIN tasks t ON tl.task_id = t.id
            WHERE tl.end_time IS NULL
            ORDER BY tl.start_time DESC
        """
        return [dict(row) for row in self.db.execute_query(query)]
    
    def get_elapsed_time(self, task_id: int) -> Optional[int]:
        """Get elapsed time for active timer in seconds."""
        active = self.db.get_active_time_log(task_id)
        if not active:
            return None
        
        start_dt = datetime.fromisoformat(active['start_time'])
        elapsed = (datetime.now() - start_dt).total_seconds()
        return int(elapsed)
    
    # ==================== TIME ANALYSIS ====================
    
    def get_task_total_time(self, task_id: int) -> int:
        """Get total time spent on a task in minutes."""
        return self.db.get_total_task_time(task_id)
    
    def get_time_logs(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all time logs for a task."""
        return self.db.get_time_logs_for_task(task_id)
    
    def get_time_by_priority(self) -> Dict[str, int]:
        """Get total time spent on tasks by priority."""
        query = """
            SELECT t.priority, COALESCE(SUM(tl.duration_minutes), 0) as total_minutes
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id AND tl.duration_minutes IS NOT NULL
            GROUP BY t.priority
            ORDER BY total_minutes DESC
        """
        result = {}
        for row in self.db.execute_query(query):
            result[row['priority']] = row['total_minutes']
        return result
    
    def get_time_by_task(self) -> List[Dict[str, Any]]:
        """Get time spent on each task, sorted by duration."""
        query = """
            SELECT 
                t.id, t.title, t.priority, t.status,
                COALESCE(SUM(tl.duration_minutes), 0) as total_minutes
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id AND tl.duration_minutes IS NOT NULL
            GROUP BY t.id
            ORDER BY total_minutes DESC
        """
        return [dict(row) for row in self.db.execute_query(query)]
    
    def get_time_by_date(self, date_str: str) -> Dict[int, int]:
        """Get total time logged for each task on a specific date."""
        query = """
            SELECT 
                t.id, t.title,
                COALESCE(SUM(tl.duration_minutes), 0) as total_minutes
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id 
                AND tl.duration_minutes IS NOT NULL
                AND DATE(tl.start_time) = ?
            GROUP BY t.id
            HAVING total_minutes > 0
            ORDER BY total_minutes DESC
        """
        result = {}
        for row in self.db.execute_query(query, (date_str,)):
            result[row['id']] = {'title': row['title'], 'minutes': row['total_minutes']}
        return result
    
    def get_average_task_duration(self) -> Dict[str, Any]:
        """Get average time spent per task."""
        query = """
            SELECT 
                COALESCE(AVG(tl.duration_minutes), 0) as avg_minutes
            FROM (
                SELECT DISTINCT id FROM tasks
            ) t
            LEFT JOIN time_logs tl ON t.id = tl.task_id AND tl.duration_minutes IS NOT NULL
        """
        result = self.db.execute_single(query)
        avg_minutes = int(result['avg_minutes']) if result else 0
        
        return {
            'average_minutes': avg_minutes,
            'average_formatted': f"{avg_minutes // 60}h {avg_minutes % 60}m" if avg_minutes > 0 else "0m"
        }
    
    def get_total_logged_time(self) -> int:
        """Get total time logged across all tasks."""
        query = "SELECT COALESCE(SUM(duration_minutes), 0) as total FROM time_logs WHERE duration_minutes IS NOT NULL"
        result = self.db.execute_single(query)
        return int(result['total']) if result and result['total'] else 0
    
    # ==================== TIME BREAKDOWN ====================
    
    def get_time_breakdown_by_priority(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed time breakdown by priority."""
        breakdown = {}
        total_time = int(self.get_total_logged_time()) if self.get_total_logged_time() else 0
        time_by_priority = self.get_time_by_priority()
        
        # Ensure all priorities are included, even if 0
        for priority in ['high', 'medium', 'low']:
            minutes = int(time_by_priority.get(priority, 0)) if time_by_priority.get(priority) else 0
            percentage = (minutes / total_time * 100) if total_time > 0 else 0
            breakdown[priority] = {
                'minutes': minutes,
                'hours': float(minutes / 60) if minutes else 0.0,
                'percentage': float(round(percentage, 1)),
                'formatted': f"{int(minutes) // 60}h {int(minutes) % 60}m" if minutes else "0h 0m"
            }
        
        return breakdown
    
    def get_time_breakdown_by_status(self) -> Dict[str, Dict[str, Any]]:
        """Get time breakdown by task status."""
        query = """
            SELECT 
                t.status,
                COALESCE(SUM(tl.duration_minutes), 0) as total_minutes
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id AND tl.duration_minutes IS NOT NULL
            GROUP BY t.status
            ORDER BY total_minutes DESC
        """
        
        breakdown = {}
        total_time = int(self.get_total_logged_time()) if self.get_total_logged_time() else 0
        time_by_status = {}
        
        for row in self.db.execute_query(query):
            try:
                status = row['status']
                minutes = int(row['total_minutes']) if row['total_minutes'] else 0
                time_by_status[status] = minutes
            except (KeyError, TypeError, ValueError) as e:
                print(f"Error processing status row: {e}")
                continue
        
        # Ensure all statuses are included, even if 0
        for status in ['not_started', 'in_progress', 'done', 'blocked']:
            minutes = time_by_status.get(status, 0)
            percentage = (minutes / total_time * 100) if total_time > 0 else 0
            breakdown[status] = {
                'minutes': int(minutes),
                'hours': float(minutes / 60) if minutes else 0.0,
                'percentage': float(round(percentage, 1)),
                'formatted': f"{int(minutes) // 60}h {int(minutes) % 60}m" if minutes else "0h 0m"
            }
        
        return breakdown
    
    # ==================== TIME PREDICTION ====================
    
    def estimate_task_completion_time(self, task_id: int) -> Dict[str, Any]:
        """Estimate time to complete a task based on similar tasks."""
        task = self.db.get_task(task_id)
        if not task:
            return {}
        
        # Get average time for similar priority tasks
        query = """
            SELECT 
                COALESCE(AVG(tl.duration_minutes), 0) as avg_minutes,
                COUNT(DISTINCT t.id) as count
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id AND tl.duration_minutes IS NOT NULL
            WHERE t.priority = ? AND t.status = 'done'
        """
        result = self.db.execute_single(query, (task['priority'],))
        
        avg_minutes = int(result['avg_minutes']) if result else 0
        count = result['count'] if result else 0
        
        return {
            'task_id': task_id,
            'task_title': task['title'],
            'priority': task['priority'],
            'estimated_minutes': avg_minutes,
            'estimated_formatted': f"{avg_minutes // 60}h {avg_minutes % 60}m" if avg_minutes > 0 else "Unknown",
            'based_on_tasks': count,
            'confidence': 'High' if count >= 3 else 'Low' if count > 0 else 'No data'
        }
    
    # ==================== TIME LOG MANAGEMENT ====================
    
    def add_manual_time_log(self, task_id: int, duration_minutes: int, date_str: str = None, notes: str = None) -> int:
        """Add a manual time log entry."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return -1
        
        if duration_minutes <= 0:
            print(f"✗ Duration must be positive")
            return -1
        
        # Create time entry
        if date_str:
            start_time = f"{date_str}T00:00:00"
        else:
            start_time = datetime.now().isoformat()
        
        end_time = datetime.fromisoformat(start_time)
        end_time = (end_time.replace(hour=0, minute=0, second=0) + 
                    __import__('datetime').timedelta(minutes=duration_minutes)).isoformat()
        
        log_id = self.db.start_time_log(task_id, start_time)
        self.db.end_time_log(log_id, end_time, notes)
        
        print(f"✓ Manual time log added: {duration_minutes} minutes for '{task['title']}'")
        return log_id
    
    def edit_time_log(self, time_log_id: int, duration_minutes: int = None, notes: str = None) -> bool:
        """Edit an existing time log entry."""
        query = "SELECT * FROM time_logs WHERE id = ?"
        log = self.db.execute_single(query, (time_log_id,))
        
        if not log:
            print(f"✗ Time log {time_log_id} not found")
            return False
        
        if duration_minutes:
            update_query = "UPDATE time_logs SET duration_minutes = ?, notes = ? WHERE id = ?"
            self.db.execute_update(update_query, (duration_minutes, notes or log['notes'], time_log_id))
        elif notes:
            update_query = "UPDATE time_logs SET notes = ? WHERE id = ?"
            self.db.execute_update(update_query, (notes, time_log_id))
        
        print(f"✓ Time log {time_log_id} updated")
        return True
    
    def delete_time_log(self, time_log_id: int) -> bool:
        """Delete a time log entry."""
        query = "DELETE FROM time_logs WHERE id = ?"
        self.db.execute_update(query, (time_log_id,))
        print(f"✓ Time log {time_log_id} deleted")
        return True
