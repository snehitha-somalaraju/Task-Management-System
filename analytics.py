"""
Analytics Engine - Handles productivity metrics and analytics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from database import Database


class Analytics:
    """
    Provides analytics and reporting capabilities for task management,
    including productivity metrics, completion rates, and trends.
    """
    
    def __init__(self, db: Database):
        """Initialize analytics engine with database instance."""
        self.db = db
    
    # ==================== DAILY ANALYTICS ====================
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Get productivity stats for today."""
        today = datetime.now().isoformat().split('T')[0]
        return self.get_date_stats(today)
    
    def get_date_stats(self, date_str: str) -> Dict[str, Any]:
        """Get productivity stats for a specific date."""
        query = """
            SELECT 
                COUNT(CASE WHEN status = 'done' AND DATE(updated_at) = ? THEN 1 END) as completed,
                COUNT(CASE WHEN DATE(created_at) = ? THEN 1 END) as created,
                COUNT(CASE WHEN status = 'done' AND DATE(updated_at) = ? AND priority = 'high' THEN 1 END) as high_completed,
                COALESCE(SUM(CASE WHEN DATE(tl.start_time) = ? THEN tl.duration_minutes ELSE 0 END), 0) as total_minutes
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id
        """
        
        result = self.db.execute_single(query, (date_str, date_str, date_str, date_str))
        
        stats = {
            'date': date_str,
            'tasks_completed': result['completed'] if result else 0,
            'tasks_created': result['created'] if result else 0,
            'high_priority_completed': result['high_completed'] if result else 0,
            'total_time_minutes': result['total_minutes'] if result else 0
        }
        
        # Format time
        minutes = stats['total_time_minutes']
        stats['total_time_formatted'] = f"{minutes // 60}h {minutes % 60}m" if minutes > 0 else "0m"
        
        # Update database stats
        self.db.upsert_productivity_stats(
            date_str,
            stats['tasks_completed'],
            stats['tasks_created'],
            stats['total_time_minutes'],
            stats['high_priority_completed']
        )
        
        return stats
    
    # ==================== PERIOD ANALYTICS ====================
    
    def get_weekly_stats(self, end_date: str = None) -> Dict[str, Any]:
        """Get productivity stats for the past week."""
        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = datetime.fromisoformat(end_date)
        
        start_date = end_date - timedelta(days=7)
        return self._get_period_stats(start_date.isoformat().split('T')[0], end_date.isoformat().split('T')[0])
    
    def get_monthly_stats(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """Get productivity stats for a specific month."""
        if year is None:
            today = datetime.now()
            year = today.year
            month = today.month
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return self._get_period_stats(start_date.isoformat().split('T')[0], end_date.isoformat().split('T')[0])
    
    def _get_period_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get stats for a date range."""
        query = """
            SELECT 
                COUNT(CASE WHEN status = 'done' AND DATE(updated_at) BETWEEN ? AND ? THEN 1 END) as completed,
                COUNT(CASE WHEN DATE(created_at) BETWEEN ? AND ? THEN 1 END) as created,
                COUNT(CASE WHEN status = 'done' AND DATE(updated_at) BETWEEN ? AND ? AND priority = 'high' THEN 1 END) as high_completed,
                COALESCE(SUM(CASE WHEN DATE(tl.start_time) BETWEEN ? AND ? THEN tl.duration_minutes ELSE 0 END), 0) as total_minutes
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id
        """
        
        result = self.db.execute_single(query, (start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date))
        
        stats = {
            'start_date': start_date,
            'end_date': end_date,
            'tasks_completed': result['completed'] if result else 0,
            'tasks_created': result['created'] if result else 0,
            'high_priority_completed': result['high_completed'] if result else 0,
            'total_time_minutes': result['total_minutes'] if result else 0
        }
        
        # Format time
        minutes = stats['total_time_minutes']
        stats['total_time_formatted'] = f"{minutes // 60}h {minutes % 60}m" if minutes > 0 else "0m"
        
        return stats
    
    # ==================== COMPLETION RATES ====================
    
    def get_completion_rate(self) -> Dict[str, Any]:
        """Calculate overall task completion rate."""
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed
            FROM tasks
        """
        result = self.db.execute_single(query)
        
        total = result['total'] if result else 0
        completed = result['completed'] if result else 0
        rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': round(rate, 1),
            'remaining_tasks': total - completed
        }
    
    def get_priority_completion_rate(self) -> Dict[str, Dict[str, Any]]:
        """Get completion rate by priority level."""
        query = """
            SELECT 
                priority,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed
            FROM tasks
            GROUP BY priority
        """
        
        result = {}
        for row in self.db.execute_query(query):
            rate = (row['completed'] / row['total'] * 100) if row['total'] > 0 else 0
            result[row['priority']] = {
                'total': row['total'],
                'completed': row['completed'],
                'completion_rate': round(rate, 1),
                'remaining': row['total'] - row['completed']
            }
        
        return result
    
    # ==================== TASK COUNTS & METRICS ====================
    
    def get_task_counts_by_status(self) -> Dict[str, int]:
        """Get count of tasks by status."""
        query = """
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
            ORDER BY count DESC
        """
        result = {}
        for row in self.db.execute_query(query):
            result[row['status']] = row['count']
        return result
    
    def get_task_counts_by_priority(self) -> Dict[str, int]:
        """Get count of tasks by priority."""
        query = """
            SELECT priority, COUNT(*) as count
            FROM tasks
            GROUP BY priority
            ORDER BY 
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END
        """
        result = {}
        for row in self.db.execute_query(query):
            result[row['priority']] = row['count']
        return result
    
    def get_tasks_completed_today(self) -> int:
        """Get count of tasks completed today."""
        today = datetime.now().isoformat().split('T')[0]
        query = "SELECT COUNT(*) as count FROM tasks WHERE status = 'done' AND DATE(updated_at) = ?"
        result = self.db.execute_single(query, (today,))
        return result['count'] if result else 0
    
    def get_tasks_completed_this_week(self) -> int:
        """Get count of tasks completed this week."""
        query = """
            SELECT COUNT(*) as count FROM tasks 
            WHERE status = 'done' 
            AND DATE(updated_at) >= DATE('now', '-7 days')
        """
        result = self.db.execute_single(query)
        return result['count'] if result else 0
    
    def get_overdue_tasks_count(self) -> int:
        """Get count of overdue tasks."""
        today = datetime.now().isoformat().split('T')[0]
        query = """
            SELECT COUNT(*) as count FROM tasks 
            WHERE status != 'done' 
            AND due_date IS NOT NULL 
            AND due_date < ?
        """
        result = self.db.execute_single(query, (today,))
        return result['count'] if result else 0
    
    def get_blocked_tasks_count(self) -> int:
        """Get count of blocked tasks."""
        query = "SELECT COUNT(*) as count FROM tasks WHERE status = 'blocked'"
        result = self.db.execute_single(query)
        return result['count'] if result else 0
    
    # ==================== TREND ANALYSIS ====================
    
    def get_completion_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily completion trend for the past N days."""
        trend = []
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).isoformat().split('T')[0]
            stats = self.get_date_stats(date)
            trend.append({
                'date': date,
                'completed': stats['tasks_completed'],
                'created': stats['tasks_created'],
                'time_minutes': stats['total_time_minutes']
            })
        return trend
    
    def get_most_productive_day(self) -> Dict[str, Any]:
        """Get the most productive day (most tasks completed)."""
        query = """
            SELECT 
                DATE(updated_at) as date,
                COUNT(*) as count
            FROM tasks
            WHERE status = 'done'
            GROUP BY DATE(updated_at)
            ORDER BY count DESC
            LIMIT 1
        """
        result = self.db.execute_single(query)
        
        if result and result['date']:
            return {
                'date': result['date'],
                'tasks_completed': result['count']
            }
        return {'date': 'N/A', 'tasks_completed': 0}
    
    def get_average_completion_time(self) -> Dict[str, Any]:
        """Get average time to complete a task."""
        query = """
            SELECT 
                COALESCE(AVG(CAST((julianday(updated_at) - julianday(created_at)) AS INTEGER)), 0) as avg_days
            FROM tasks
            WHERE status = 'done'
        """
        result = self.db.execute_single(query)
        avg_days = result['avg_days'] if result else 0
        
        return {
            'average_days': round(avg_days, 1),
            'average_hours': round(avg_days * 24, 1)
        }
    
    # ==================== DETAILED REPORTS ====================
    
    def get_productivity_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive productivity dashboard."""
        today = self.get_today_stats()
        weekly = self.get_weekly_stats()
        completion_rate = self.get_completion_rate()
        priority_rate = self.get_priority_completion_rate()
        status_counts = self.get_task_counts_by_status()
        priority_counts = self.get_task_counts_by_priority()
        
        return {
            'today': today,
            'weekly': weekly,
            'completion_rate': completion_rate,
            'priority_completion': priority_rate,
            'task_status_distribution': status_counts,
            'task_priority_distribution': priority_counts,
            'overdue_count': self.get_overdue_tasks_count(),
            'blocked_count': self.get_blocked_tasks_count(),
            'most_productive_day': self.get_most_productive_day(),
            'avg_completion_time': self.get_average_completion_time()
        }
    
    def get_weekly_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown of past 7 days."""
        breakdown = {}
        for i in range(7, 0, -1):
            date = (datetime.now() - timedelta(days=i)).isoformat().split('T')[0]
            day_name = (datetime.now() - timedelta(days=i)).strftime('%A')
            stats = self.get_date_stats(date)
            breakdown[day_name] = stats
        return breakdown
    
    def get_priority_analysis(self) -> Dict[str, Any]:
        """Get detailed analysis by priority."""
        query = """
            SELECT 
                priority,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'blocked' THEN 1 END) as blocked,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COALESCE(SUM(tl.duration_minutes), 0) as total_time
            FROM tasks t
            LEFT JOIN time_logs tl ON t.id = tl.task_id AND tl.duration_minutes IS NOT NULL
            GROUP BY priority
        """
        
        analysis = {}
        for row in self.db.execute_query(query):
            priority = row['priority']
            analysis[priority] = {
                'total_tasks': row['total'],
                'completed': row['completed'],
                'blocked': row['blocked'],
                'in_progress': row['in_progress'],
                'pending': row['total'] - row['completed'] - row['blocked'] - row['in_progress'],
                'total_time_minutes': row['total_time'],
                'total_time_formatted': f"{row['total_time'] // 60}h {row['total_time'] % 60}m"
            }
        
        return analysis
