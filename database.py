"""
Database Layer - Handles all database operations for Task Management System
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Any, Tuple, Optional


class Database:
    """
    Database management class for SQLite3 operations.
    Handles connection management, schema creation, and CRUD operations.
    """
    
    def __init__(self, db_name: str = "tasks.db"):
        """Initialize database connection and create tables if needed."""
        self.db_name = db_name
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self._create_connection()
        self._create_tables()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _create_connection(self):
        """Create initial database connection and check connectivity."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            print(f"[OK] Database connected: {self.db_path}")
        except sqlite3.Error as e:
            print(f"✗ Database connection error: {e}")
            raise
    
    def _create_tables(self):
        """Create all required tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table 0: users (NEW - for authentication)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Table 1: tasks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT DEFAULT 'medium' CHECK(priority IN ('high', 'medium', 'low')),
                    status TEXT DEFAULT 'not_started' CHECK(status IN ('not_started', 'in_progress', 'done', 'blocked')),
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_recurring BOOLEAN DEFAULT 0,
                    recurring_pattern_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (recurring_pattern_id) REFERENCES recurring_patterns(id)
                )
            """)
            
            # Table 2: task_dependencies
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    depends_on_task_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    UNIQUE(task_id, depends_on_task_id)
                )
            """)
            
            # Table 3: recurring_patterns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recurring_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    frequency TEXT NOT NULL CHECK(frequency IN ('daily', 'weekly', 'monthly')),
                    interval INTEGER DEFAULT 1,
                    end_date TEXT,
                    days_of_week TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Table 4: time_logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes INTEGER,
                    notes TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            # Table 5: productivity_stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productivity_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_created INTEGER DEFAULT 0,
                    total_time_minutes INTEGER DEFAULT 0,
                    high_priority_completed INTEGER DEFAULT 0,
                    calculated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            print("[OK] Database tables created/verified")
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute SELECT query and return results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_single(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """Execute SELECT query and return single result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query, return last inserted row ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """Execute multiple INSERT/UPDATE/DELETE queries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
    
    # ==================== TASK OPERATIONS ====================
    
    def create_task(self, title: str, description: str = "", priority: str = "medium",
                    due_date: str = None, is_recurring: bool = False,
                    recurring_pattern_id: int = None) -> int:
        """Create a new task and return its ID."""
        now = datetime.now().isoformat()
        query = """
            INSERT INTO tasks 
            (title, description, priority, status, due_date, created_at, updated_at, is_recurring, recurring_pattern_id)
            VALUES (?, ?, ?, 'not_started', ?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (title, description, priority, due_date, now, now, is_recurring, recurring_pattern_id))
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        query = "SELECT * FROM tasks WHERE id = ?"
        result = self.execute_single(query, (task_id,))
        return dict(result) if result else None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        query = "SELECT * FROM tasks ORDER BY due_date, priority DESC"
        return [dict(row) for row in self.execute_query(query)]
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get tasks by status."""
        query = "SELECT * FROM tasks WHERE status = ? ORDER BY due_date, priority DESC"
        return [dict(row) for row in self.execute_query(query, (status,))]
    
    def get_tasks_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Get tasks by priority level."""
        query = "SELECT * FROM tasks WHERE priority = ? ORDER BY due_date, created_at"
        return [dict(row) for row in self.execute_query(query, (priority,))]
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """Update task fields. Only updates fields provided in kwargs."""
        allowed_fields = {'title', 'description', 'priority', 'status', 'due_date', 'is_recurring', 'recurring_pattern_id'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return False
        
        update_fields['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
        query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
        
        self.execute_update(query, tuple(update_fields.values()) + (task_id,))
        return True
    
    def delete_task(self, task_id: int) -> bool:
        """Delete task and cascade delete related data."""
        query = "DELETE FROM tasks WHERE id = ?"
        self.execute_update(query, (task_id,))
        return True
    
    # ==================== DEPENDENCY OPERATIONS ====================
    
    def add_dependency(self, task_id: int, depends_on_task_id: int) -> int:
        """Add dependency relationship between tasks."""
        now = datetime.now().isoformat()
        query = """
            INSERT INTO task_dependencies (task_id, depends_on_task_id, created_at)
            VALUES (?, ?, ?)
        """
        return self.execute_update(query, (task_id, depends_on_task_id, now))
    
    def get_dependencies(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all tasks that a task depends on."""
        query = """
            SELECT t.* FROM tasks t
            JOIN task_dependencies td ON t.id = td.depends_on_task_id
            WHERE td.task_id = ?
        """
        return [dict(row) for row in self.execute_query(query, (task_id,))]
    
    def get_dependents(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all tasks that depend on this task."""
        query = """
            SELECT t.* FROM tasks t
            JOIN task_dependencies td ON t.id = td.task_id
            WHERE td.depends_on_task_id = ?
        """
        return [dict(row) for row in self.execute_query(query, (task_id,))]
    
    def remove_dependency(self, task_id: int, depends_on_task_id: int) -> bool:
        """Remove dependency relationship."""
        query = "DELETE FROM task_dependencies WHERE task_id = ? AND depends_on_task_id = ?"
        self.execute_update(query, (task_id, depends_on_task_id))
        return True
    
    def get_all_dependencies(self) -> List[Dict[str, Any]]:
        """Get all dependencies."""
        query = """
            SELECT td.*, t1.title as task_title, t2.title as depends_on_title
            FROM task_dependencies td
            JOIN tasks t1 ON td.task_id = t1.id
            JOIN tasks t2 ON td.depends_on_task_id = t2.id
        """
        return [dict(row) for row in self.execute_query(query)]
    
    # ==================== RECURRING PATTERN OPERATIONS ====================
    
    def create_recurring_pattern(self, frequency: str, interval: int = 1,
                                 end_date: str = None, days_of_week: str = None) -> int:
        """Create recurring pattern and return its ID."""
        now = datetime.now().isoformat()
        query = """
            INSERT INTO recurring_patterns (frequency, interval, end_date, days_of_week, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (frequency, interval, end_date, days_of_week, now))
    
    def get_recurring_pattern(self, pattern_id: int) -> Optional[Dict[str, Any]]:
        """Get recurring pattern by ID."""
        query = "SELECT * FROM recurring_patterns WHERE id = ?"
        result = self.execute_single(query, (pattern_id,))
        return dict(result) if result else None
    
    def get_recurring_tasks(self) -> List[Dict[str, Any]]:
        """Get all recurring tasks."""
        query = "SELECT * FROM tasks WHERE is_recurring = 1 ORDER BY created_at"
        return [dict(row) for row in self.execute_query(query)]
    
    # ==================== TIME LOGGING OPERATIONS ====================
    
    def start_time_log(self, task_id: int, start_time: str = None) -> int:
        """Start a new time log entry."""
        if start_time is None:
            start_time = datetime.now().isoformat()
        query = """
            INSERT INTO time_logs (task_id, start_time)
            VALUES (?, ?)
        """
        return self.execute_update(query, (task_id, start_time))
    
    def end_time_log(self, time_log_id: int, end_time: str = None, notes: str = None) -> bool:
        """End a time log entry and calculate duration."""
        if end_time is None:
            end_time = datetime.now().isoformat()
        
        # Get start_time to calculate duration
        log = self.execute_single("SELECT start_time FROM time_logs WHERE id = ?", (time_log_id,))
        if not log:
            return False
        
        start_dt = datetime.fromisoformat(log['start_time'])
        end_dt = datetime.fromisoformat(end_time)
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        query = """
            UPDATE time_logs 
            SET end_time = ?, duration_minutes = ?, notes = ?
            WHERE id = ?
        """
        self.execute_update(query, (end_time, duration_minutes, notes, time_log_id))
        return True
    
    def get_time_logs_for_task(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all time logs for a task."""
        query = "SELECT * FROM time_logs WHERE task_id = ? ORDER BY start_time DESC"
        return [dict(row) for row in self.execute_query(query, (task_id,))]
    
    def get_active_time_log(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent active time log for a task (end_time is NULL)."""
        query = """
            SELECT * FROM time_logs
            WHERE task_id = ? AND end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1
        """
        row = self.execute_single(query, (task_id,))
        return dict(row) if row else None

    
    def get_total_task_time(self, task_id: int) -> int:
        """Get total time spent on a task in minutes."""
        query = "SELECT COALESCE(SUM(duration_minutes), 0) as total FROM time_logs WHERE task_id = ? AND duration_minutes IS NOT NULL"
        result = self.execute_single(query, (task_id,))
        return result['total'] if result else 0
    
    # ==================== PRODUCTIVITY STATS OPERATIONS ====================
    
    def upsert_productivity_stats(self, date: str, tasks_completed: int = 0,
                                  tasks_created: int = 0, total_time_minutes: int = 0,
                                  high_priority_completed: int = 0) -> int:
        """Create or update productivity stats for a date."""
        now = datetime.now().isoformat()
        query = """
            INSERT INTO productivity_stats 
            (date, tasks_completed, tasks_created, total_time_minutes, high_priority_completed, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                tasks_completed = excluded.tasks_completed,
                tasks_created = excluded.tasks_created,
                total_time_minutes = excluded.total_time_minutes,
                high_priority_completed = excluded.high_priority_completed,
                calculated_at = excluded.calculated_at
        """
        return self.execute_update(query, (date, tasks_completed, tasks_created, total_time_minutes, high_priority_completed, now))
    
    def get_productivity_stats(self, date: str) -> Optional[Dict[str, Any]]:
        """Get productivity stats for a specific date."""
        query = "SELECT * FROM productivity_stats WHERE date = ?"
        result = self.execute_single(query, (date,))
        return dict(result) if result else None
    
    def get_productivity_stats_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get productivity stats for a date range."""
        query = "SELECT * FROM productivity_stats WHERE date BETWEEN ? AND ? ORDER BY date"
        return [dict(row) for row in self.execute_query(query, (start_date, end_date))]
    
    # ==================== UTILITY OPERATIONS ====================
    
    def clear_database(self) -> bool:
        """Clear all data from database (for testing)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tables = ['time_logs', 'task_dependencies', 'productivity_stats', 'tasks', 'recurring_patterns']
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            conn.commit()
        return True
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get statistics about database content."""
        stats = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tables = ['tasks', 'task_dependencies', 'recurring_patterns', 'time_logs', 'productivity_stats']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
        return stats
