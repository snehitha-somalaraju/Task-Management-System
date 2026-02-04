"""
Test suite for Task Management System
Tests all major features and functionality
"""

import os
import sys
from datetime import datetime, timedelta

# Import modules
from database import Database
from task_manager import TaskManager
from time_tracker import TimeTracker
from analytics import Analytics
from calendar_exporter import CalendarExporter


class TaskManagementSystemTests:
    """Test suite for all system components"""
    
    def __init__(self):
        """Initialize test environment"""
        self.db = Database("test_tasks.db")
        self.task_manager = TaskManager(self.db)
        self.time_tracker = TimeTracker(self.db)
        self.analytics = Analytics(self.db)
        self.calendar_exporter = CalendarExporter(self.db)
        self.test_count = 0
        self.passed = 0
        self.failed = 0
    
    def print_test(self, name: str, result: bool, message: str = ""):
        """Print test result"""
        self.test_count += 1
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{self.test_count:2d}. {status} - {name}")
        if message:
            print(f"     {message}")
        if result:
            self.passed += 1
        else:
            self.failed += 1
    
    def cleanup(self):
        """Clean up test database"""
        if os.path.exists(self.db.db_path):
            os.remove(self.db.db_path)
    
    # ==================== DATABASE TESTS ====================
    
    def test_database_connection(self):
        """Test database connection"""
        try:
            stats = self.db.get_database_stats()
            result = isinstance(stats, dict) and 'tasks' in stats
            self.print_test("Database Connection", result)
        except Exception as e:
            self.print_test("Database Connection", False, str(e))
    
    def test_task_creation(self):
        """Test task creation"""
        try:
            task_id = self.db.create_task("Test Task", "Description", "high")
            task = self.db.get_task(task_id)
            result = task and task['title'] == "Test Task"
            self.print_test("Task Creation", result)
        except Exception as e:
            self.print_test("Task Creation", False, str(e))
    
    def test_task_retrieval(self):
        """Test task retrieval"""
        try:
            task_id = self.db.create_task("Retrieve Test", "Test", "medium")
            tasks = self.db.get_all_tasks()
            result = len(tasks) > 0 and any(t['id'] == task_id for t in tasks)
            self.print_test("Task Retrieval", result)
        except Exception as e:
            self.print_test("Task Retrieval", False, str(e))
    
    def test_task_update(self):
        """Test task update"""
        try:
            task_id = self.db.create_task("Update Test", "Original", "low")
            self.db.update_task(task_id, description="Updated", priority="high")
            task = self.db.get_task(task_id)
            result = task['description'] == "Updated" and task['priority'] == "high"
            self.print_test("Task Update", result)
        except Exception as e:
            self.print_test("Task Update", False, str(e))
    
    def test_task_deletion(self):
        """Test task deletion"""
        try:
            task_id = self.db.create_task("Delete Test", "Test", "low")
            self.db.delete_task(task_id)
            task = self.db.get_task(task_id)
            result = task is None
            self.print_test("Task Deletion", result)
        except Exception as e:
            self.print_test("Task Deletion", False, str(e))
    
    # ==================== DEPENDENCY TESTS ====================
    
    def test_add_dependency(self):
        """Test adding task dependency"""
        try:
            task1 = self.db.create_task("Task 1", "First", "high")
            task2 = self.db.create_task("Task 2", "Second", "high")
            dep_id = self.task_manager.add_dependency(task2, task1)
            result = dep_id is not None
            self.print_test("Add Dependency", result)
        except Exception as e:
            self.print_test("Add Dependency", False, str(e))
    
    def test_circular_dependency_prevention(self):
        """Test circular dependency prevention"""
        try:
            task1 = self.db.create_task("Task 1", "First", "high")
            task2 = self.db.create_task("Task 2", "Second", "high")
            self.task_manager.add_dependency(task2, task1)
            # Try to create circular dependency
            result = self.task_manager._has_circular_dependency(task1, task2)
            self.print_test("Circular Dependency Prevention", result)
        except Exception as e:
            self.print_test("Circular Dependency Prevention", False, str(e))
    
    def test_get_dependencies(self):
        """Test retrieving task dependencies"""
        try:
            task1 = self.db.create_task("Task 1", "First", "high")
            task2 = self.db.create_task("Task 2", "Second", "high")
            self.db.add_dependency(task2, task1)
            deps = self.db.get_dependencies(task2)
            result = len(deps) > 0 and deps[0]['id'] == task1
            self.print_test("Get Dependencies", result)
        except Exception as e:
            self.print_test("Get Dependencies", False, str(e))
    
    # ==================== RECURRING TASK TESTS ====================
    
    def test_create_recurring_pattern(self):
        """Test creating recurring pattern"""
        try:
            pattern_id = self.db.create_recurring_pattern("weekly", 1, None, "Monday")
            pattern = self.db.get_recurring_pattern(pattern_id)
            result = pattern and pattern['frequency'] == "weekly"
            self.print_test("Create Recurring Pattern", result)
        except Exception as e:
            self.print_test("Create Recurring Pattern", False, str(e))
    
    def test_create_recurring_task(self):
        """Test creating recurring task"""
        try:
            task_id = self.task_manager.create_recurring_task(
                "Weekly Meeting", "Team sync", "medium", "weekly"
            )
            task = self.db.get_task(task_id)
            result = task and task['is_recurring'] == 1
            self.print_test("Create Recurring Task", result)
        except Exception as e:
            self.print_test("Create Recurring Task", False, str(e))
    
    def test_generate_recurring_instances(self):
        """Test generating recurring task instances"""
        try:
            task_id = self.task_manager.create_recurring_task(
                "Daily Task", "Daily work", "high", "daily"
            )
            task = self.db.get_task(task_id)
            instances = self.task_manager.generate_recurring_instances(
                task['recurring_pattern_id'], 5
            )
            result = len(instances) == 5
            self.print_test("Generate Recurring Instances", result)
        except Exception as e:
            self.print_test("Generate Recurring Instances", False, str(e))
    
    # ==================== TIME TRACKING TESTS ====================
    
    def test_start_timer(self):
        """Test starting timer"""
        try:
            task_id = self.db.create_task("Timer Test", "Test", "high")
            log_id = self.time_tracker.start_timer(task_id)
            result = log_id > 0
            self.print_test("Start Timer", result)
        except Exception as e:
            self.print_test("Start Timer", False, str(e))
    
    def test_stop_timer(self):
        """Test stopping timer"""
        try:
            task_id = self.db.create_task("Timer Stop Test", "Test", "high")
            self.time_tracker.start_timer(task_id)
            result = self.time_tracker.stop_timer(task_id)
            self.print_test("Stop Timer", result)
        except Exception as e:
            self.print_test("Stop Timer", False, str(e))
    
    def test_time_logs(self):
        """Test time log retrieval"""
        try:
            task_id = self.db.create_task("Time Log Test", "Test", "high")
            self.time_tracker.start_timer(task_id)
            self.time_tracker.stop_timer(task_id)
            logs = self.time_tracker.get_time_logs(task_id)
            result = len(logs) > 0
            self.print_test("Time Logs", result)
        except Exception as e:
            self.print_test("Time Logs", False, str(e))
    
    def test_total_task_time(self):
        """Test calculating total task time"""
        try:
            task_id = self.db.create_task("Total Time Test", "Test", "high")
            self.time_tracker.start_timer(task_id)
            self.time_tracker.stop_timer(task_id)
            total = self.time_tracker.get_task_total_time(task_id)
            result = total > 0
            self.print_test("Total Task Time", result)
        except Exception as e:
            self.print_test("Total Task Time", False, str(e))
    
    # ==================== ANALYTICS TESTS ====================
    
    def test_today_stats(self):
        """Test getting today's stats"""
        try:
            task_id = self.db.create_task("Today Test", "Test", "high")
            self.db.update_task(task_id, status="done")
            stats = self.analytics.get_today_stats()
            result = stats and 'tasks_completed' in stats
            self.print_test("Today Stats", result)
        except Exception as e:
            self.print_test("Today Stats", False, str(e))
    
    def test_completion_rate(self):
        """Test completion rate calculation"""
        try:
            self.db.create_task("Task 1", "Test", "high")
            task_id = self.db.create_task("Task 2", "Test", "high")
            self.db.update_task(task_id, status="done")
            rate = self.analytics.get_completion_rate()
            result = rate and rate['completion_rate'] > 0
            self.print_test("Completion Rate", result)
        except Exception as e:
            self.print_test("Completion Rate", False, str(e))
    
    def test_task_counts_by_status(self):
        """Test task count by status"""
        try:
            self.db.create_task("Task 1", "Test", "high")
            task_id = self.db.create_task("Task 2", "Test", "high")
            self.db.update_task(task_id, status="in_progress")
            counts = self.analytics.get_task_counts_by_status()
            result = counts and 'not_started' in counts
            self.print_test("Task Counts by Status", result)
        except Exception as e:
            self.print_test("Task Counts by Status", False, str(e))
    
    def test_productivity_dashboard(self):
        """Test productivity dashboard generation"""
        try:
            dashboard = self.analytics.get_productivity_dashboard()
            result = dashboard and 'today' in dashboard and 'completion_rate' in dashboard
            self.print_test("Productivity Dashboard", result)
        except Exception as e:
            self.print_test("Productivity Dashboard", False, str(e))
    
    def test_priority_analysis(self):
        """Test priority analysis"""
        try:
            self.db.create_task("High Task", "Test", "high")
            self.db.create_task("Medium Task", "Test", "medium")
            analysis = self.analytics.get_priority_analysis()
            result = analysis and 'high' in analysis and 'medium' in analysis
            self.print_test("Priority Analysis", result)
        except Exception as e:
            self.print_test("Priority Analysis", False, str(e))
    
    # ==================== CALENDAR EXPORT TESTS ====================
    
    def test_export_to_ics(self):
        """Test exporting tasks to ICS format"""
        try:
            self.db.create_task("Export Test", "Test task", "high", "2024-12-31")
            result = self.calendar_exporter.export_tasks_to_ics("test_export.ics")
            self.print_test("Export to ICS", result)
            # Clean up
            if os.path.exists(os.path.join(os.path.dirname(__file__), "test_export.ics")):
                os.remove(os.path.join(os.path.dirname(__file__), "test_export.ics"))
        except Exception as e:
            self.print_test("Export to ICS", False, str(e))
    
    def test_export_undone_tasks(self):
        """Test exporting only undone tasks"""
        try:
            self.db.create_task("Undone Task", "Test", "high")
            task_id = self.db.create_task("Done Task", "Test", "high")
            self.db.update_task(task_id, status="done")
            result = self.calendar_exporter.export_undone_tasks("test_undone.ics")
            self.print_test("Export Undone Tasks", result)
            # Clean up
            if os.path.exists(os.path.join(os.path.dirname(__file__), "test_undone.ics")):
                os.remove(os.path.join(os.path.dirname(__file__), "test_undone.ics"))
        except Exception as e:
            self.print_test("Export Undone Tasks", False, str(e))
    
    # ==================== TASK MANAGER TESTS ====================
    
    def test_start_task(self):
        """Test starting a task"""
        try:
            task_id = self.db.create_task("Start Test", "Test", "high")
            result = self.task_manager.start_task(task_id)
            task = self.db.get_task(task_id)
            result = result and task['status'] == 'in_progress'
            self.print_test("Start Task", result)
        except Exception as e:
            self.print_test("Start Task", False, str(e))
    
    def test_complete_task(self):
        """Test completing a task"""
        try:
            task_id = self.db.create_task("Complete Test", "Test", "high")
            result = self.task_manager.complete_task(task_id)
            task = self.db.get_task(task_id)
            result = result and task['status'] == 'done'
            self.print_test("Complete Task", result)
        except Exception as e:
            self.print_test("Complete Task", False, str(e))
    
    def test_get_blocked_tasks(self):
        """Test getting blocked tasks"""
        try:
            task1 = self.db.create_task("Task 1", "Test", "high")
            task2 = self.db.create_task("Task 2", "Test", "high")
            self.task_manager.add_dependency(task2, task1)
            blocked = self.task_manager.get_blocked_tasks()
            result = len(blocked) > 0
            self.print_test("Get Blocked Tasks", result)
        except Exception as e:
            self.print_test("Get Blocked Tasks", False, str(e))
    
    def test_get_available_tasks(self):
        """Test getting available tasks"""
        try:
            task1 = self.db.create_task("Task 1", "Test", "high")
            task2 = self.db.create_task("Task 2", "Test", "high")
            available = self.task_manager.get_available_tasks()
            result = len(available) >= 2
            self.print_test("Get Available Tasks", result)
        except Exception as e:
            self.print_test("Get Available Tasks", False, str(e))
    
    # ==================== RUN ALL TESTS ====================
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("TASK MANAGEMENT SYSTEM - TEST SUITE".center(70))
        print("=" * 70 + "\n")
        
        # Database tests
        print("DATABASE TESTS:")
        self.test_database_connection()
        self.test_task_creation()
        self.test_task_retrieval()
        self.test_task_update()
        self.test_task_deletion()
        
        # Dependency tests
        print("\nDEPENDENCY TESTS:")
        self.test_add_dependency()
        self.test_circular_dependency_prevention()
        self.test_get_dependencies()
        
        # Recurring task tests
        print("\nRECURRING TASK TESTS:")
        self.test_create_recurring_pattern()
        self.test_create_recurring_task()
        self.test_generate_recurring_instances()
        
        # Time tracking tests
        print("\nTIME TRACKING TESTS:")
        self.test_start_timer()
        self.test_stop_timer()
        self.test_time_logs()
        self.test_total_task_time()
        
        # Analytics tests
        print("\nANALYTICS TESTS:")
        self.test_today_stats()
        self.test_completion_rate()
        self.test_task_counts_by_status()
        self.test_productivity_dashboard()
        self.test_priority_analysis()
        
        # Calendar export tests
        print("\nCALENDAR EXPORT TESTS:")
        self.test_export_to_ics()
        self.test_export_undone_tasks()
        
        # Task manager tests
        print("\nTASK MANAGER TESTS:")
        self.test_start_task()
        self.test_complete_task()
        self.test_get_blocked_tasks()
        self.test_get_available_tasks()
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY".center(70))
        print("=" * 70)
        print(f"Total Tests:  {self.test_count}")
        print(f"Passed:       {self.passed} ✓")
        print(f"Failed:       {self.failed} ✗")
        print(f"Success Rate: {(self.passed/self.test_count*100):.1f}%")
        print("=" * 70 + "\n")
        
        # Cleanup
        self.cleanup()
        
        return self.failed == 0


def main():
    """Run test suite"""
    tests = TaskManagementSystemTests()
    success = tests.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
