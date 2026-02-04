"""
Task Manager Module - Handles task operations, dependencies, and recurring tasks
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Optional, Set
from database import Database


class TaskManager:
    """
    Manages all task-related operations including creation, editing,
    dependency management, and recurring task generation.
    """
    
    def __init__(self, db: Database):
        """Initialize task manager with database instance."""
        self.db = db
    
    # ==================== TASK CREATION & EDITING ====================
    
    def create_task(self, title: str, description: str = "", priority: str = "medium",
                    due_date: str = None) -> int:
        """Create a simple (non-recurring) task."""
        if priority not in ['high', 'medium', 'low']:
            raise ValueError(f"Invalid priority: {priority}. Must be 'high', 'medium', or 'low'")
        
        task_id = self.db.create_task(title, description, priority, due_date, is_recurring=False)
        print(f"✓ Task created: '{title}' (ID: {task_id})")
        return task_id
    
    def create_recurring_task(self, title: str, description: str = "", priority: str = "medium",
                              frequency: str = "weekly", interval: int = 1,
                              end_date: str = None, days_of_week: str = None) -> int:
        """Create a recurring task."""
        if frequency not in ['daily', 'weekly', 'monthly']:
            raise ValueError(f"Invalid frequency: {frequency}")
        
        # Create recurring pattern first
        pattern_id = self.db.create_recurring_pattern(frequency, interval, end_date, days_of_week)
        
        # Create initial task with pattern reference
        task_id = self.db.create_task(title, description, priority, None, is_recurring=True, recurring_pattern_id=pattern_id)
        print(f"✓ Recurring task created: '{title}' (Pattern: {frequency}, ID: {task_id})")
        return task_id
    
    def edit_task(self, task_id: int, **kwargs) -> bool:
        """Edit task properties."""
        allowed_fields = {'title', 'description', 'priority', 'status', 'due_date'}
        
        # Validate priority if provided
        if 'priority' in kwargs and kwargs['priority'] not in ['high', 'medium', 'low']:
            raise ValueError(f"Invalid priority: {kwargs['priority']}")
        
        # Validate status if provided
        if 'status' in kwargs and kwargs['status'] not in ['not_started', 'in_progress', 'done', 'blocked']:
            raise ValueError(f"Invalid status: {kwargs['status']}")
        
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if self.db.update_task(task_id, **update_data):
            print(f"✓ Task {task_id} updated")
            return True
        return False
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task and all its related data."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return False
        
        self.db.delete_task(task_id)
        print(f"✓ Task '{task['title']}' deleted")
        return True
    
    # ==================== TASK RETRIEVAL ====================
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task details."""
        return self.db.get_task(task_id)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        return self.db.get_all_tasks()
    
    def get_available_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are ready to start (not blocked by dependencies)."""
        all_tasks = self.db.get_all_tasks()
        available = []
        
        for task in all_tasks:
            if task['status'] != 'blocked':
                # Check if any dependencies are incomplete
                dependencies = self.db.get_dependencies(task['id'])
                if all(dep['status'] == 'done' for dep in dependencies):
                    available.append(task)
        
        return available
    
    def get_blocked_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are blocked by incomplete dependencies."""
        blocked = []
        all_tasks = self.db.get_all_tasks()
        
        for task in all_tasks:
            dependencies = self.db.get_dependencies(task['id'])
            if dependencies and any(dep['status'] != 'done' for dep in dependencies):
                blocked.append(task)
        
        return blocked
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are overdue."""
        now = datetime.now().isoformat().split('T')[0]
        all_tasks = self.db.get_all_tasks()
        return [t for t in all_tasks if t['due_date'] and t['due_date'] < now and t['status'] != 'done']
    
    def get_tasks_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Get tasks filtered by priority."""
        return self.db.get_tasks_by_priority(priority)
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get tasks filtered by status."""
        return self.db.get_tasks_by_status(status)
    
    # ==================== DEPENDENCY MANAGEMENT ====================
    
    def add_dependency(self, task_id: int, depends_on_task_id: int) -> bool:
        """Add dependency: task_id depends on depends_on_task_id."""
        # Validate tasks exist
        if not self.db.get_task(task_id):
            print(f"✗ Task {task_id} not found")
            return False
        
        if not self.db.get_task(depends_on_task_id):
            print(f"✗ Task {depends_on_task_id} not found")
            return False
        
        # Check for circular dependency
        if self._has_circular_dependency(task_id, depends_on_task_id):
            print(f"✗ Circular dependency detected!")
            return False
        
        # Check if dependency already exists
        dependencies = self.db.get_dependencies(task_id)
        if any(d['id'] == depends_on_task_id for d in dependencies):
            print(f"✗ Dependency already exists")
            return False
        
        self.db.add_dependency(task_id, depends_on_task_id)
        task = self.db.get_task(task_id)
        dep_task = self.db.get_task(depends_on_task_id)
        print(f"✓ Dependency added: '{task['title']}' depends on '{dep_task['title']}'")
        
        # Update task status to blocked if dependency is incomplete
        if dep_task['status'] != 'done':
            self.db.update_task(task_id, status='blocked')
        
        return True
    
    def remove_dependency(self, task_id: int, depends_on_task_id: int) -> bool:
        """Remove dependency between tasks."""
        if self.db.remove_dependency(task_id, depends_on_task_id):
            print(f"✓ Dependency removed")
            
            # Check if task should be unblocked
            task = self.db.get_task(task_id)
            if task['status'] == 'blocked':
                dependencies = self.db.get_dependencies(task_id)
                if not dependencies or all(d['status'] == 'done' for d in dependencies):
                    self.db.update_task(task_id, status='not_started')
            
            return True
        return False
    
    def get_dependency_tree(self, task_id: int) -> Dict[str, Any]:
        """Get dependency tree for a task (recursive structure)."""
        task = self.db.get_task(task_id)
        if not task:
            return {}
        
        dependencies = self.db.get_dependencies(task_id)
        dependents = self.db.get_dependents(task_id)
        
        return {
            'task': task,
            'depends_on': [self.get_dependency_tree(d['id']) for d in dependencies],
            'required_by': [{'id': d['id'], 'title': d['title']} for d in dependents]
        }
    
    def _has_circular_dependency(self, task_id: int, depends_on_task_id: int) -> bool:
        """Check if adding dependency would create a cycle using DFS."""
        visited: Set[int] = set()
        
        def has_path(from_id: int, to_id: int) -> bool:
            if from_id == to_id:
                return True
            if from_id in visited:
                return False
            
            visited.add(from_id)
            dependencies = self.db.get_dependencies(from_id)
            
            for dep in dependencies:
                if has_path(dep['id'], to_id):
                    return True
            
            return False
        
        return has_path(depends_on_task_id, task_id)
    
    # ==================== TASK STATUS MANAGEMENT ====================
    
    def start_task(self, task_id: int) -> bool:
        """Mark task as in_progress."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return False
        
        # Check dependencies
        dependencies = self.db.get_dependencies(task_id)
        if dependencies and any(d['status'] != 'done' for d in dependencies):
            print(f"✗ Cannot start task: dependencies not completed")
            return False
        
        self.db.update_task(task_id, status='in_progress')
        print(f"✓ Task '{task['title']}' started")
        return True
    
    def complete_task(self, task_id: int) -> bool:
        """Mark task as done and update dependent tasks."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return False
        
        # Stop any active timer before marking as done
        active_timer = self.db.get_active_time_log(task_id)
        if active_timer:
            self.time_tracker.stop_timer(task_id)
        
        self.db.update_task(task_id, status='done')
        print(f"✓ Task '{task['title']}' completed")
        
        # Unblock dependent tasks
        dependents = self.db.get_dependents(task_id)
        for dependent in dependents:
            # Check if all dependencies of dependent are done
            dependencies = self.db.get_dependencies(dependent['id'])
            if all(d['status'] == 'done' for d in dependencies):
                self.db.update_task(dependent['id'], status='not_started')
                print(f"  → Task '{dependent['title']}' is now available")
        
        return True
    
    def block_task(self, task_id: int) -> bool:
        """Mark task as blocked."""
        task = self.db.get_task(task_id)
        if not task:
            print(f"✗ Task {task_id} not found")
            return False
        
        self.db.update_task(task_id, status='blocked')
        print(f"✓ Task '{task['title']}' blocked")
        return True
    
    # ==================== RECURRING TASK GENERATION ====================
    
    def generate_recurring_instances(self, recurring_pattern_id: int, num_occurrences: int = 10) -> List[int]:
        """Generate future instances of a recurring task."""
        pattern = self.db.get_recurring_pattern(recurring_pattern_id)
        if not pattern:
            return []
        
        # Find the original recurring task
        tasks = self.db.execute_query(
            "SELECT * FROM tasks WHERE recurring_pattern_id = ? AND is_recurring = 1",
            (recurring_pattern_id,)
        )
        
        if not tasks:
            return []
        
        original_task = dict(tasks[0])
        generated_ids = []
        
        start_date = datetime.now()
        
        for i in range(num_occurrences):
            if pattern['frequency'] == 'daily':
                next_date = start_date + timedelta(days=i * pattern['interval'])
            elif pattern['frequency'] == 'weekly':
                next_date = start_date + timedelta(weeks=i * pattern['interval'])
            elif pattern['frequency'] == 'monthly':
                next_date = start_date + relativedelta(months=i * pattern['interval'])
            else:
                continue
            
            # Check if within end_date
            if pattern['end_date'] and next_date.date() > datetime.fromisoformat(pattern['end_date']).date():
                break
            
            # Create instance
            instance_id = self.db.create_task(
                title=original_task['title'],
                description=original_task['description'],
                priority=original_task['priority'],
                due_date=next_date.isoformat().split('T')[0],
                is_recurring=False,
                recurring_pattern_id=None
            )
            generated_ids.append(instance_id)
        
        return generated_ids
    
    # ==================== TASK SUMMARY ====================
    
    def get_task_summary(self, task_id: int) -> Dict[str, Any]:
        """Get comprehensive summary of a task including dependencies and time logs."""
        task = self.db.get_task(task_id)
        if not task:
            return {}
        
        dependencies = self.db.get_dependencies(task_id)
        dependents = self.db.get_dependents(task_id)
        time_logs = self.db.get_time_logs_for_task(task_id)
        total_time = self.db.get_total_task_time(task_id)
        
        return {
            'task': task,
            'dependencies': dependencies,
            'dependents': dependents,
            'time_logs': time_logs,
            'total_time_minutes': total_time,
            'total_time_formatted': f"{total_time // 60}h {total_time % 60}m" if total_time > 0 else "0m"
        }
