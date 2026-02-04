"""
Display Module - Handles console UI and formatting
"""

from datetime import datetime
from typing import List, Dict, Any
from tabulate import tabulate
from colorama import Fore, Back, Style, init
from database import Database


# Initialize colorama for cross-platform colors
init(autoreset=True)


class Display:
    """
    Handles all console output and formatting including tables,
    colored text, and data visualization.
    """
    
    # Color schemes
    PRIORITY_COLORS = {
        'high': Fore.RED,
        'medium': Fore.YELLOW,
        'low': Fore.GREEN
    }
    
    STATUS_COLORS = {
        'done': Fore.GREEN,
        'in_progress': Fore.CYAN,
        'blocked': Fore.RED,
        'not_started': Fore.WHITE
    }
    
    def __init__(self, db: Database):
        """Initialize display with database instance."""
        self.db = db
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def _colored_text(self, text: str, color: str) -> str:
        """Return colored text."""
        return f"{color}{text}{Style.RESET_ALL}"
    
    def _format_priority(self, priority: str) -> str:
        """Format priority with color."""
        color = self.PRIORITY_COLORS.get(priority, Fore.WHITE)
        icon_map = {'high': '⚠️', 'medium': '⚡', 'low': '✓'}
        icon = icon_map.get(priority, '•')
        return self._colored_text(f"{icon} {priority.upper()}", color)
    
    def _format_status(self, status: str) -> str:
        """Format status with color."""
        color = self.STATUS_COLORS.get(status, Fore.WHITE)
        icon_map = {
            'done': '✓',
            'in_progress': '⟳',
            'blocked': '⊗',
            'not_started': '◯'
        }
        icon = icon_map.get(status, '•')
        return self._colored_text(f"{icon} {status}", color)
    
    def _format_date(self, date_str: str) -> str:
        """Format date with color based on urgency."""
        if not date_str:
            return "-"
        
        try:
            due = datetime.fromisoformat(date_str).date()
            today = datetime.now().date()
            
            if due < today:
                return self._colored_text(f"🔴 {date_str}", Fore.RED)
            elif (due - today).days <= 3:
                return self._colored_text(f"🟡 {date_str}", Fore.YELLOW)
            else:
                return f"🟢 {date_str}"
        except:
            return date_str
    
    # ==================== TABLE DISPLAY ====================
    
    def display_tasks_table(self, tasks: List[Dict[str, Any]], full: bool = False) -> None:
        """Display tasks in a formatted table."""
        if not tasks:
            print(self._colored_text("No tasks found.", Fore.YELLOW))
            return
        
        headers = ["ID", "Title", "Priority", "Status", "Due Date", "Time"]
        if full:
            headers.append("Description")
        
        rows = []
        for task in tasks:
            total_time = self.db.get_total_task_time(task['id'])
            time_str = f"{total_time // 60}h {total_time % 60}m" if total_time > 0 else "-"
            
            row = [
                task['id'],
                task['title'][:50],  # Truncate long titles
                self._format_priority(task['priority']),
                self._format_status(task['status']),
                self._format_date(task['due_date']),
                time_str
            ]
            
            if full:
                row.append(task['description'][:50] if task['description'] else "-")
            
            rows.append(row)
        
        print("\n" + tabulate(rows, headers=headers, tablefmt="grid", showindex=False))
    
    def display_task_detail(self, task_id: int) -> None:
        """Display detailed information about a task."""
        task = self.db.get_task(task_id)
        if not task:
            print(self._colored_text(f"Task {task_id} not found.", Fore.RED))
            return
        
        print("\n" + "=" * 60)
        print(self._colored_text(f"TASK #{task['id']}: {task['title']}", Fore.CYAN) + Style.RESET_ALL)
        print("=" * 60)
        
        # Basic info
        print(f"\n{Fore.CYAN}Basic Information:{Style.RESET_ALL}")
        print(f"  Priority:    {self._format_priority(task['priority'])}")
        print(f"  Status:      {self._format_status(task['status'])}")
        print(f"  Created:     {task['created_at']}")
        print(f"  Updated:     {task['updated_at']}")
        
        # Dates
        print(f"\n{Fore.CYAN}Dates:{Style.RESET_ALL}")
        print(f"  Due Date:    {self._format_date(task['due_date'])}")
        
        # Description
        if task['description']:
            print(f"\n{Fore.CYAN}Description:{Style.RESET_ALL}")
            print(f"  {task['description']}")
        
        # Dependencies
        dependencies = self.db.get_dependencies(task['id'])
        if dependencies:
            print(f"\n{Fore.CYAN}Depends On:{Style.RESET_ALL}")
            for dep in dependencies:
                status_color = self.STATUS_COLORS.get(dep['status'], Fore.WHITE)
                print(f"  • {dep['title']} ({self._colored_text(dep['status'], status_color)})")
        
        # Dependents
        dependents = self.db.get_dependents(task['id'])
        if dependents:
            print(f"\n{Fore.CYAN}Required By:{Style.RESET_ALL}")
            for dep in dependents:
                status_color = self.STATUS_COLORS.get(dep['status'], Fore.WHITE)
                print(f"  • {dep['title']} ({self._colored_text(dep['status'], status_color)})")
        
        # Time tracking
        total_time = self.db.get_total_task_time(task['id'])
        time_logs = self.db.get_time_logs_for_task(task['id'])
        
        print(f"\n{Fore.CYAN}Time Tracking:{Style.RESET_ALL}")
        print(f"  Total Time:  {total_time // 60}h {total_time % 60}m")
        print(f"  Sessions:    {len(time_logs)}")
        
        if time_logs:
            print(f"\n{Fore.CYAN}Time Log History:{Style.RESET_ALL}")
            for log in time_logs[:5]:  # Show last 5
                duration = log['duration_minutes'] if log['duration_minutes'] else "running"
                notes_part = f"({log['notes']})" if log['notes'] else ""
                print(f"  • {log['start_time'][:10]} - {duration} min {notes_part}")
        
        print("\n" + "=" * 60 + "\n")
    
    def display_dependency_tree(self, task_id: int, depth: int = 0, max_depth: int = 5) -> None:
        """Display dependency tree for a task."""
        if depth == 0:
            print("\n" + self._colored_text("DEPENDENCY TREE", Fore.CYAN) + Style.RESET_ALL)
            print("=" * 60)
        
        if depth > max_depth:
            return
        
        task = self.db.get_task(task_id)
        if not task:
            return
        
        indent = "  " * depth
        status_color = self.STATUS_COLORS.get(task['status'], Fore.WHITE)
        status_icon = "✓" if task['status'] == 'done' else "→" if task['status'] == 'in_progress' else "◯"
        
        if depth == 0:
            print(f"\n{indent}{Fore.GREEN}ROOT: {task['title']}{Style.RESET_ALL}")
        else:
            status_text = self._colored_text(f"({task['status']})", status_color)
            print(f"{indent}{status_icon} {task['title']} {status_text}")
        
        # Show dependencies
        dependencies = self.db.get_dependencies(task_id)
        if dependencies:
            for i, dep in enumerate(dependencies):
                is_last = i == len(dependencies) - 1
                connector = "└─" if is_last else "├─"
                print(f"{indent}{connector} REQUIRES:")
                self.display_dependency_tree(dep['id'], depth + 1, max_depth)
        
        if depth == 0:
            print("\n" + "=" * 60 + "\n")
    
    # ==================== ANALYTICS DISPLAY ====================
    
    def display_productivity_dashboard(self, dashboard: Dict[str, Any]) -> None:
        """Display comprehensive productivity dashboard."""
        print("\n" + self._colored_text("═" * 70, Fore.CYAN))
        print(self._colored_text("PRODUCTIVITY DASHBOARD", Fore.CYAN))
        print(self._colored_text("═" * 70, Fore.CYAN))
        
        # Today's stats
        today = dashboard['today']
        print(f"\n{Fore.CYAN}TODAY'S STATS:{Style.RESET_ALL}")
        print(f"  Tasks Completed: {self._colored_text(str(today['tasks_completed']), Fore.GREEN)}")
        print(f"  Tasks Created:   {today['tasks_created']}")
        print(f"  Time Logged:     {today['total_time_formatted']}")
        print(f"  High Priority Done: {self._colored_text(str(today['high_priority_completed']), Fore.RED)}")
        
        # Weekly stats
        weekly = dashboard['weekly']
        print(f"\n{Fore.CYAN}WEEKLY STATS (Last 7 Days):{Style.RESET_ALL}")
        print(f"  Tasks Completed: {self._colored_text(str(weekly['tasks_completed']), Fore.GREEN)}")
        print(f"  Tasks Created:   {weekly['tasks_created']}")
        print(f"  Time Logged:     {weekly['total_time_formatted']}")
        
        # Completion rate
        comp = dashboard['completion_rate']
        rate_color = Fore.GREEN if comp['completion_rate'] >= 70 else Fore.YELLOW if comp['completion_rate'] >= 50 else Fore.RED
        print(f"\n{Fore.CYAN}COMPLETION RATE:{Style.RESET_ALL}")
        rate_text = self._colored_text(f"{comp['completion_rate']}%", rate_color)
        print(f"  Overall: {rate_text} ({comp['completed_tasks']}/{comp['total_tasks']})")
        
        # Priority breakdown
        priority_comp = dashboard['priority_completion']
        print(f"\n{Fore.CYAN}COMPLETION BY PRIORITY:{Style.RESET_ALL}")
        for priority in ['high', 'medium', 'low']:
            if priority in priority_comp:
                p = priority_comp[priority]
                print(f"  {self._format_priority(priority)}: {p['completion_rate']}% ({p['completed']}/{p['total']})")
        
        # Status distribution
        status_dist = dashboard['task_status_distribution']
        print(f"\n{Fore.CYAN}TASK STATUS DISTRIBUTION:{Style.RESET_ALL}")
        for status, count in status_dist.items():
            status_color = self.STATUS_COLORS.get(status, Fore.WHITE)
            print(f"  {self._colored_text(status, status_color)}: {count}")
        
        # Alerts
        print(f"\n{Fore.CYAN}ALERTS:{Style.RESET_ALL}")
        if dashboard['overdue_count'] > 0:
            overdue_text = self._colored_text(f"⚠ {dashboard['overdue_count']} OVERDUE TASKS", Fore.RED)
            print(f"  {overdue_text}")
        if dashboard['blocked_count'] > 0:
            blocked_text = self._colored_text(f"⊗ {dashboard['blocked_count']} BLOCKED TASKS", Fore.YELLOW)
            print(f"  {blocked_text}")
        
        # Most productive day
        most_prod = dashboard['most_productive_day']
        if most_prod['date'] != 'N/A':
            print(f"  Most Productive Day: {most_prod['date']} ({most_prod['tasks_completed']} tasks)")
        
        avg_time = dashboard['avg_completion_time']
        print(f"  Avg Completion Time: {avg_time['average_days']} days")
        
        print(f"\n{Fore.CYAN}═══════════════════════════════════════════════════════════════════{Style.RESET_ALL}\n")
    
    def display_priority_analysis(self, analysis: Dict[str, Dict[str, Any]]) -> None:
        """Display priority-based analysis."""
        print("\n" + self._colored_text("PRIORITY ANALYSIS", Fore.CYAN) + Style.RESET_ALL)
        print("=" * 70)
        
        headers = ["Priority", "Total", "Completed", "In Progress", "Blocked", "Pending", "Time"]
        rows = []
        
        for priority in ['high', 'medium', 'low']:
            if priority in analysis:
                a = analysis[priority]
                rows.append([
                    self._format_priority(priority),
                    a['total_tasks'],
                    self._colored_text(str(a['completed']), Fore.GREEN),
                    self._colored_text(str(a['in_progress']), Fore.CYAN),
                    self._colored_text(str(a['blocked']), Fore.RED),
                    a['pending'],
                    a['total_time_formatted']
                ])
        
        print("\n" + tabulate(rows, headers=headers, tablefmt="grid", showindex=False))
        print()
    
    # ==================== CHARTS (TEXT-BASED) ====================
    
    def display_completion_trend(self, trend: List[Dict[str, Any]]) -> None:
        """Display simple text-based trend chart."""
        print("\n" + self._colored_text("COMPLETION TREND (Last 7 Days)", Fore.CYAN) + Style.RESET_ALL)
        print("=" * 70)
        
        max_tasks = max([t['completed'] for t in trend]) if trend else 1
        
        for day in trend:
            bar_length = int((day['completed'] / max(max_tasks, 1)) * 40)
            bar = "█" * bar_length
            print(f"{day['date']}: {self._colored_text(bar, Fore.GREEN)} {day['completed']}")
        
        print()
    
    def display_time_breakdown(self, breakdown: Dict[str, Dict[str, Any]]) -> None:
        """Display time breakdown by category."""
        print("\n" + self._colored_text("TIME BREAKDOWN", Fore.CYAN) + Style.RESET_ALL)
        print("=" * 70)
        
        headers = ["Category", "Hours", "Percentage", "Visual"]
        rows = []
        
        for category, data in breakdown.items():
            percentage = data['percentage']
            bar_length = int(percentage / 5)
            bar = "█" * bar_length
            
            rows.append([
                category.replace('_', ' ').title(),
                f"{data['hours']:.1f}",
                f"{percentage}%",
                bar
            ])
        
        print("\n" + tabulate(rows, headers=headers, tablefmt="simple", showindex=False))
        print()
    
    # ==================== STATUS DISPLAY ====================
    
    def display_status_summary(self) -> None:
        """Display system status summary."""
        from analytics import Analytics
        analytics = Analytics(self.db)
        
        dashboard = analytics.get_productivity_dashboard()
        
        print("\n" + self._colored_text("SYSTEM STATUS", Fore.CYAN) + Style.RESET_ALL)
        print("=" * 70)
        
        comp = dashboard['completion_rate']
        
        # Overall progress bar
        bar_length = int((comp['completion_rate'] / 100) * 40)
        bar = self._colored_text("█" * bar_length, Fore.GREEN) + "░" * (40 - bar_length)
        print(f"\nOverall Progress: [{bar}] {comp['completion_rate']}%")
        print(f"Completed: {comp['completed_tasks']} | Total: {comp['total_tasks']} | Remaining: {comp['remaining_tasks']}")
        
        # Alerts
        if dashboard['overdue_count'] > 0 or dashboard['blocked_count'] > 0:
            print(f"\n{Fore.YELLOW}WARNINGS:{Style.RESET_ALL}")
            if dashboard['overdue_count'] > 0:
                overdue_alert = self._colored_text(f"{dashboard['overdue_count']} overdue tasks", Fore.RED)
                print(f"  • {overdue_alert}")
            if dashboard['blocked_count'] > 0:
                blocked_alert = self._colored_text(f"{dashboard['blocked_count']} blocked tasks", Fore.YELLOW)
                print(f"  • {blocked_alert}")
        
        print()
    
    # ==================== MENU DISPLAY ====================
    
    def display_main_menu(self) -> None:
        """Display main menu."""
        print("\n" + self._colored_text("═" * 70, Fore.CYAN))
        print(self._colored_text("TASK MANAGEMENT SYSTEM", Fore.CYAN))
        print(self._colored_text("═" * 70, Fore.CYAN))
        print("""
    {cyan}TASKS{reset}
    1. List all tasks
    2. View task details
    3. Create new task
    4. Create recurring task
    5. Edit task
    6. Delete task
    7. Update task status
    
    {cyan}DEPENDENCIES{reset}
    8. Add dependency
    9. Remove dependency
    10. View dependency tree
    
    {cyan}TIME TRACKING{reset}
    11. Start timer
    12. Stop timer
    13. View time logs
    14. Add manual time log
    
    {cyan}ANALYTICS{reset}
    15. View dashboard
    16. View productivity report
    17. View priority analysis
    18. Export to calendar
    
    {cyan}SYSTEM{reset}
    19. View database stats
    20. Exit
        """.format(cyan=Fore.CYAN, reset=Style.RESET_ALL))
    
    def display_task_menu(self, task_id: int) -> None:
        """Display menu for a specific task."""
        task = self.db.get_task(task_id)
        if not task:
            print(self._colored_text(f"Task {task_id} not found", Fore.RED))
            return
        
        print(f"\n{Fore.CYAN}TASK #{task_id}: {task['title']}{Style.RESET_ALL}")
        print("""
    1. View details
    2. Edit task
    3. Change status
    4. Add time log
    5. View time logs
    6. Add dependency
    7. View dependencies
    8. Back to main menu
        """)
