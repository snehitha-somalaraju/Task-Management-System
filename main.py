"""
Main Application - Menu-driven interface for Task Management System
"""

import sys
from datetime import datetime
from database import Database
from task_manager import TaskManager
from time_tracker import TimeTracker
from analytics import Analytics
from calendar_exporter import CalendarExporter
from display import Display


class TaskManagementApp:
    """
    Main application class that orchestrates all modules
    and provides the user interface.
    """
    
    def __init__(self):
        """Initialize the application."""
        print("\n" + "=" * 70)
        print("INITIALIZING TASK MANAGEMENT SYSTEM".center(70))
        print("=" * 70 + "\n")
        
        # Initialize modules
        self.db = Database("tasks.db")
        self.task_manager = TaskManager(self.db)
        self.time_tracker = TimeTracker(self.db)
        self.analytics = Analytics(self.db)
        self.calendar_exporter = CalendarExporter(self.db)
        self.display = Display(self.db)
        
        print("✓ All modules initialized\n")
    
    def run(self):
        """Main application loop."""
        while True:
            try:
                self.display.display_main_menu()
                choice = input("\nSelect option (1-20): ").strip()
                
                if choice == "1":
                    self.list_tasks()
                elif choice == "2":
                    self.view_task_details()
                elif choice == "3":
                    self.create_task()
                elif choice == "4":
                    self.create_recurring_task()
                elif choice == "5":
                    self.edit_task()
                elif choice == "6":
                    self.delete_task()
                elif choice == "7":
                    self.update_task_status()
                elif choice == "8":
                    self.add_dependency()
                elif choice == "9":
                    self.remove_dependency()
                elif choice == "10":
                    self.view_dependency_tree()
                elif choice == "11":
                    self.start_timer()
                elif choice == "12":
                    self.stop_timer()
                elif choice == "13":
                    self.view_time_logs()
                elif choice == "14":
                    self.add_manual_time_log()
                elif choice == "15":
                    self.view_dashboard()
                elif choice == "16":
                    self.view_productivity_report()
                elif choice == "17":
                    self.view_priority_analysis()
                elif choice == "18":
                    self.export_calendar()
                elif choice == "19":
                    self.view_database_stats()
                elif choice == "20":
                    self.exit_app()
                else:
                    print("✗ Invalid option. Please try again.")
            
            except KeyboardInterrupt:
                print("\n\n✓ Application interrupted by user")
                break
            except Exception as e:
                print(f"\n✗ Error: {e}\n")
    
    # ==================== TASK OPERATIONS ====================
    
    def list_tasks(self):
        """List all tasks."""
        print("\n" + "=" * 70)
        print("ALL TASKS".center(70))
        print("=" * 70)
        
        # Show filter options
        print("\n1. All tasks")
        print("2. By status")
        print("3. By priority")
        print("4. Available (unblocked)")
        print("5. Blocked tasks")
        print("6. Overdue tasks")
        
        choice = input("\nSelect filter (1-6): ").strip()
        
        if choice == "1":
            tasks = self.task_manager.get_all_tasks()
        elif choice == "2":
            statuses = ['not_started', 'in_progress', 'done', 'blocked']
            for i, s in enumerate(statuses, 1):
                print(f"{i}. {s}")
            status_choice = input("Select status: ").strip()
            try:
                status = statuses[int(status_choice) - 1]
                tasks = self.task_manager.get_tasks_by_status(status)
            except:
                print("✗ Invalid choice")
                return
        elif choice == "3":
            priorities = ['high', 'medium', 'low']
            for i, p in enumerate(priorities, 1):
                print(f"{i}. {p}")
            priority_choice = input("Select priority: ").strip()
            try:
                priority = priorities[int(priority_choice) - 1]
                tasks = self.task_manager.get_tasks_by_priority(priority)
            except:
                print("✗ Invalid choice")
                return
        elif choice == "4":
            tasks = self.task_manager.get_available_tasks()
        elif choice == "5":
            tasks = self.task_manager.get_blocked_tasks()
        elif choice == "6":
            tasks = self.task_manager.get_overdue_tasks()
        else:
            print("✗ Invalid choice")
            return
        
        self.display.display_tasks_table(tasks, full=False)
    
    def view_task_details(self):
        """View details of a specific task."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            self.display.display_task_detail(task_id)
        except ValueError:
            print("✗ Invalid task ID")
    
    def create_task(self):
        """Create a new task."""
        print("\n" + "=" * 70)
        print("CREATE NEW TASK".center(70))
        print("=" * 70)
        
        title = input("\nTask title: ").strip()
        if not title:
            print("✗ Title cannot be empty")
            return
        
        description = input("Description (optional): ").strip()
        
        # Priority
        print("\nPriority:")
        for i, p in enumerate(['high', 'medium', 'low'], 1):
            print(f"{i}. {p}")
        priority_choice = input("Select priority (1-3) [2]: ").strip() or "2"
        try:
            priority = ['high', 'medium', 'low'][int(priority_choice) - 1]
        except:
            priority = 'medium'
        
        # Due date
        due_date = input("Due date (YYYY-MM-DD) or press Enter to skip: ").strip()
        if due_date:
            try:
                datetime.fromisoformat(due_date)
            except:
                print("✗ Invalid date format")
                return
        else:
            due_date = None
        
        task_id = self.task_manager.create_task(title, description, priority, due_date)
        print(f"\n✓ Task {task_id} created successfully")
    
    def create_recurring_task(self):
        """Create a recurring task."""
        print("\n" + "=" * 70)
        print("CREATE RECURRING TASK".center(70))
        print("=" * 70)
        
        title = input("\nTask title: ").strip()
        if not title:
            print("✗ Title cannot be empty")
            return
        
        description = input("Description (optional): ").strip()
        
        # Frequency
        print("\nFrequency:")
        frequencies = ['daily', 'weekly', 'monthly']
        for i, f in enumerate(frequencies, 1):
            print(f"{i}. {f}")
        freq_choice = input("Select frequency (1-3): ").strip()
        try:
            frequency = frequencies[int(freq_choice) - 1]
        except:
            print("✗ Invalid choice")
            return
        
        interval = input("Interval (default 1): ").strip()
        try:
            interval = int(interval) if interval else 1
        except:
            interval = 1
        
        end_date = input("End date (YYYY-MM-DD) or press Enter for no end: ").strip() or None
        
        priority = input("Priority (high/medium/low) [medium]: ").strip() or "medium"
        
        task_id = self.task_manager.create_recurring_task(
            title, description, priority, frequency, interval, end_date
        )
        
        # Generate first instances
        print("\nGenerating recurring instances...")
        num = input("Number of instances to generate [10]: ").strip()
        try:
            num = int(num) if num else 10
        except:
            num = 10
        
        pattern = self.db.get_recurring_pattern(self.db.get_task(task_id)['recurring_pattern_id'])
        if pattern:
            instances = self.task_manager.generate_recurring_instances(pattern['id'], num)
            print(f"✓ Generated {len(instances)} instances")
    
    def edit_task(self):
        """Edit a task."""
        try:
            task_id = int(input("\nEnter task ID to edit: ").strip())
            task = self.task_manager.get_task(task_id)
            
            if not task:
                print("✗ Task not found")
                return
            
            print(f"\nCurrent task: {task['title']}")
            print("Leave empty to keep current value\n")
            
            title = input(f"Title [{task['title']}]: ").strip()
            description = input(f"Description [{task['description']}]: ").strip()
            priority = input(f"Priority [{task['priority']}]: ").strip()
            due_date = input(f"Due date [{task['due_date']}]: ").strip()
            
            updates = {}
            if title:
                updates['title'] = title
            if description:
                updates['description'] = description
            if priority:
                updates['priority'] = priority
            if due_date:
                updates['due_date'] = due_date
            
            if updates:
                self.task_manager.edit_task(task_id, **updates)
            else:
                print("✓ No changes made")
        
        except ValueError:
            print("✗ Invalid task ID")
    
    def delete_task(self):
        """Delete a task."""
        try:
            task_id = int(input("\nEnter task ID to delete: ").strip())
            task = self.task_manager.get_task(task_id)
            
            if not task:
                print("✗ Task not found")
                return
            
            confirm = input(f"Delete '{task['title']}'? (y/n): ").strip().lower()
            if confirm == 'y':
                self.task_manager.delete_task(task_id)
            else:
                print("✓ Cancelled")
        
        except ValueError:
            print("✗ Invalid task ID")
    
    def update_task_status(self):
        """Update task status."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            task = self.task_manager.get_task(task_id)
            
            if not task:
                print("✗ Task not found")
                return
            
            print(f"\nTask: {task['title']}")
            print("Current status:", task['status'])
            
            statuses = ['not_started', 'in_progress', 'done', 'blocked']
            print("\nNew status:")
            for i, s in enumerate(statuses, 1):
                print(f"{i}. {s}")
            
            status_choice = input("Select status (1-4): ").strip()
            try:
                status = statuses[int(status_choice) - 1]
                if status == 'done':
                    self.task_manager.complete_task(task_id)
                elif status == 'in_progress':
                    self.task_manager.start_task(task_id)
                elif status == 'blocked':
                    self.task_manager.block_task(task_id)
                else:
                    self.db.update_task(task_id, status=status)
                    print(f"✓ Status updated to {status}")
            except:
                print("✗ Invalid choice")
        
        except ValueError:
            print("✗ Invalid task ID")
    
    # ==================== DEPENDENCY OPERATIONS ====================
    
    def add_dependency(self):
        """Add task dependency."""
        try:
            task_id = int(input("\nEnter task ID that depends on another: ").strip())
            depends_on_id = int(input("Enter task ID it depends on: ").strip())
            
            self.task_manager.add_dependency(task_id, depends_on_id)
        
        except ValueError:
            print("✗ Invalid task ID")
    
    def remove_dependency(self):
        """Remove task dependency."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            depends_on_id = int(input("Enter dependency task ID to remove: ").strip())
            
            self.task_manager.remove_dependency(task_id, depends_on_id)
        
        except ValueError:
            print("✗ Invalid task ID")
    
    def view_dependency_tree(self):
        """View dependency tree for a task."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            self.display.display_dependency_tree(task_id)
        except ValueError:
            print("✗ Invalid task ID")
    
    # ==================== TIME TRACKING OPERATIONS ====================
    
    def start_timer(self):
        """Start timer for a task."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            self.time_tracker.start_timer(task_id)
        except ValueError:
            print("✗ Invalid task ID")
    
    def stop_timer(self):
        """Stop timer for a task."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            notes = input("Notes (optional): ").strip()
            self.time_tracker.stop_timer(task_id, notes or None)
        except ValueError:
            print("✗ Invalid task ID")
    
    def view_time_logs(self):
        """View time logs for a task."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            logs = self.time_tracker.get_time_logs(task_id)
            total = self.time_tracker.get_task_total_time(task_id)
            
            print(f"\n{'='*70}")
            print(f"Time logs for task {task_id}".center(70))
            print(f"{'='*70}")
            print(f"Total time: {total // 60}h {total % 60}m\n")
            
            if logs:
                from tabulate import tabulate
                headers = ["Start", "End", "Duration (min)", "Notes"]
                rows = [
                    [l['start_time'][:10], l['end_time'][:10] if l['end_time'] else "Running", l['duration_minutes'] or "—", l['notes'] or "—"]
                    for l in logs
                ]
                print(tabulate(rows, headers=headers, tablefmt="grid"))
            else:
                print("No time logs found")
            print()
        
        except ValueError:
            print("✗ Invalid task ID")
    
    def add_manual_time_log(self):
        """Add manual time log."""
        try:
            task_id = int(input("\nEnter task ID: ").strip())
            minutes = int(input("Duration (minutes): ").strip())
            date_str = input("Date (YYYY-MM-DD) or press Enter for today: ").strip() or None
            notes = input("Notes (optional): ").strip()
            
            self.time_tracker.add_manual_time_log(task_id, minutes, date_str, notes or None)
        
        except ValueError:
            print("✗ Invalid input")
    
    # ==================== ANALYTICS OPERATIONS ====================
    
    def view_dashboard(self):
        """View productivity dashboard."""
        dashboard = self.analytics.get_productivity_dashboard()
        self.display.display_productivity_dashboard(dashboard)
        self.display.display_status_summary()
    
    def view_productivity_report(self):
        """View productivity report."""
        print("\n" + "=" * 70)
        print("PRODUCTIVITY REPORT".center(70))
        print("=" * 70)
        
        print("\n1. Today's report")
        print("2. Weekly report")
        print("3. Monthly report")
        print("4. Completion trend (7 days)")
        
        choice = input("\nSelect report (1-4): ").strip()
        
        if choice == "1":
            stats = self.analytics.get_today_stats()
            print(f"\nToday ({stats['date']}):")
            print(f"  Tasks completed: {stats['tasks_completed']}")
            print(f"  Tasks created: {stats['tasks_created']}")
            print(f"  High priority done: {stats['high_priority_completed']}")
            print(f"  Time logged: {stats['total_time_formatted']}")
        
        elif choice == "2":
            stats = self.analytics.get_weekly_stats()
            print(f"\nWeek ({stats['start_date']} to {stats['end_date']}):")
            print(f"  Tasks completed: {stats['tasks_completed']}")
            print(f"  Tasks created: {stats['tasks_created']}")
            print(f"  Time logged: {stats['total_time_formatted']}")
        
        elif choice == "3":
            year = input("Year [current]: ").strip()
            month = input("Month (1-12) [current]: ").strip()
            try:
                year = int(year) if year else None
                month = int(month) if month else None
            except:
                pass
            
            stats = self.analytics.get_monthly_stats(year, month)
            print(f"\nMonth ({stats['start_date']} to {stats['end_date']}):")
            print(f"  Tasks completed: {stats['tasks_completed']}")
            print(f"  Tasks created: {stats['tasks_created']}")
            print(f"  Time logged: {stats['total_time_formatted']}")
        
        elif choice == "4":
            trend = self.analytics.get_completion_trend(7)
            self.display.display_completion_trend(trend)
        
        print()
    
    def view_priority_analysis(self):
        """View priority-based analysis."""
        analysis = self.analytics.get_priority_analysis()
        self.display.display_priority_analysis(analysis)
    
    # ==================== EXPORT OPERATIONS ====================
    
    def export_calendar(self):
        """Export tasks to calendar format."""
        print("\n" + "=" * 70)
        print("EXPORT TO CALENDAR".center(70))
        print("=" * 70)
        
        print("\n1. All tasks")
        print("2. Incomplete tasks")
        print("3. By priority")
        print("4. Overdue tasks")
        
        choice = input("\nSelect export type (1-4): ").strip()
        
        filename = input("Output filename (without .ics): ").strip()
        if not filename:
            filename = "tasks"
        filename += ".ics"
        
        if choice == "1":
            self.calendar_exporter.export_tasks_to_ics(filename)
        elif choice == "2":
            self.calendar_exporter.export_undone_tasks(filename)
        elif choice == "3":
            print("\n1. High priority")
            print("2. Medium priority")
            print("3. Low priority")
            priority_choice = input("Select priority (1-3): ").strip()
            try:
                priority = ['high', 'medium', 'low'][int(priority_choice) - 1]
                self.calendar_exporter.export_priority_tasks(priority, filename)
            except:
                print("✗ Invalid choice")
        elif choice == "4":
            self.calendar_exporter.export_overdue_tasks(filename)
        else:
            print("✗ Invalid choice")
    
    # ==================== SYSTEM OPERATIONS ====================
    
    def view_database_stats(self):
        """View database statistics."""
        print("\n" + "=" * 70)
        print("DATABASE STATISTICS".center(70))
        print("=" * 70)
        
        stats = self.db.get_database_stats()
        
        print(f"\nDatabase: {self.db.db_path}")
        print("\nTable contents:")
        from tabulate import tabulate
        rows = [[k, v] for k, v in stats.items()]
        print(tabulate(rows, headers=["Table", "Records"], tablefmt="grid"))
        
        # Additional stats
        print("\n" + "=" * 70)
        completion_rate = self.analytics.get_completion_rate()
        print(f"Completion Rate: {completion_rate['completion_rate']}%")
        print(f"Total Time Logged: {self.time_tracker.get_total_logged_time() // 60}h")
        print()
    
    def exit_app(self):
        """Exit application."""
        print("\n✓ Thank you for using Task Management System!")
        print("Goodbye!\n")
        sys.exit(0)


def main():
    """Entry point for the application."""
    try:
        app = TaskManagementApp()
        app.run()
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
