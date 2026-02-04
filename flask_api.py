"""
Flask REST API for Task Management System
Provides complete REST API for all operations
"""

from flask import Flask, jsonify, request, send_file, render_template, session
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import io
import os
import secrets

from database import Database
from task_manager import TaskManager
from time_tracker import TimeTracker
from analytics import Analytics
from calendar_exporter import CalendarExporter
from google_calendar_sync import GoogleCalendarSync
from service_account_sync import ServiceAccountCalendarSync
from user_manager import UserManager
from googleapiclient.discovery import build


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime and other non-serializable objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
app.json_encoder = CustomJSONEncoder
app.secret_key = secrets.token_hex(32)  # For session management
CORS(app)

# Initialize modules
db = Database("tasks.db")
task_manager = TaskManager(db)
time_tracker = TimeTracker(db)
analytics = Analytics(db)
calendar_exporter = CalendarExporter(db)
google_calendar_sync = GoogleCalendarSync(db)  # Initialize Google Calendar sync
service_account_sync = ServiceAccountCalendarSync(db)  # Initialize Service Account sync
user_manager = UserManager(db)  # Initialize User Manager


# ==================== ERROR HANDLERS ====================

@app.errorhandler(500)
def handle_500_error(e):
    """Global 500 error handler"""
    print(f"500 ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    return jsonify({'error': str(e), 'type': 'internal_server_error'}), 500


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Register a new user"""
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        success, message, user_id = user_manager.register_user(username, email, password)
        
        if success:
            # Create session token
            token = secrets.token_urlsafe(32)
            session['user_id'] = user_id
            session['username'] = username
            session['token'] = token
            
            return jsonify({
                'status': 'success',
                'message': message,
                'user_id': user_id,
                'username': username,
                'token': token
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and create session"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        success, message, user_id = user_manager.login_user(username, password)
        
        if success:
            # Create session
            token = secrets.token_urlsafe(32)
            session['user_id'] = user_id
            session['username'] = username
            session['token'] = token
            
            return jsonify({
                'status': 'success',
                'message': message,
                'user_id': user_id,
                'username': username,
                'token': token
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    try:
        session.clear()
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auth/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = user_manager.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'status': 'success',
            'user': user
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auth/profile', methods=['PUT'])
def update_profile():
    """Update user profile"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.json
        email = data.get('email')
        username = data.get('username')
        
        success = user_manager.update_user(user_id, email=email, username=username)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Profile updated successfully'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update profile'
            }), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({
                'status': 'error',
                'message': 'Old and new passwords are required'
            }), 400
        
        success, message = user_manager.change_password(user_id, old_password, new_password)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auth/verify-session', methods=['GET'])
def verify_session():
    """Verify if user has an active session"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        if user_id:
            return jsonify({
                'status': 'authenticated',
                'user_id': user_id,
                'username': username
            }), 200
        else:
            return jsonify({
                'status': 'not_authenticated'
            }), 401
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== HEALTH CHECK ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        stats = db.get_database_stats()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database_tables': stats
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== TASK ENDPOINTS ====================

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks with optional filtering"""
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        if status:
            tasks = task_manager.get_tasks_by_status(status)
        elif priority:
            tasks = task_manager.get_tasks_by_priority(priority)
        else:
            tasks = task_manager.get_all_tasks()
        
        return jsonify([dict(t) for t in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get single task with details"""
    try:
        summary = task_manager.get_task_summary(task_id)
        if not summary:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create new task"""
    try:
        data = request.json
        title = data.get('title')
        description = data.get('description', '')
        priority = data.get('priority', 'medium')
        due_date = data.get('due_date')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        task_id = task_manager.create_task(title, description, priority, due_date)
        return jsonify({'id': task_id, 'message': 'Task created'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update task"""
    try:
        data = request.json
        if task_manager.edit_task(task_id, **data):
            return jsonify({'message': 'Task updated'})
        return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete task"""
    try:
        if task_manager.delete_task(task_id):
            return jsonify({'message': 'Task deleted'})
        return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/status/<int:task_id>', methods=['PUT'])
def update_task_status(task_id):
    """Update task status"""
    try:
        data = request.json
        status = data.get('status')
        
        if status == 'done':
            task_manager.complete_task(task_id)
        elif status == 'in_progress':
            task_manager.start_task(task_id)
        elif status == 'blocked':
            task_manager.block_task(task_id)
        else:
            db.update_task(task_id, status=status)
        
        return jsonify({'message': f'Status updated to {status}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== TASK FILTERING ENDPOINTS ====================

@app.route('/api/tasks/available', methods=['GET'])
def get_available_tasks():
    """Get available (unblocked) tasks"""
    try:
        tasks = task_manager.get_available_tasks()
        return jsonify([dict(t) for t in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/blocked', methods=['GET'])
def get_blocked_tasks():
    """Get blocked tasks"""
    try:
        tasks = task_manager.get_blocked_tasks()
        return jsonify([dict(t) for t in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/overdue', methods=['GET'])
def get_overdue_tasks():
    """Get overdue tasks"""
    try:
        tasks = task_manager.get_overdue_tasks()
        return jsonify([dict(t) for t in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== RECURRING TASK ENDPOINTS ====================

@app.route('/api/tasks/recurring', methods=['POST'])
def create_recurring_task():
    """Create recurring task"""
    try:
        data = request.json
        task_id = task_manager.create_recurring_task(
            title=data.get('title'),
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            frequency=data.get('frequency', 'weekly'),
            interval=data.get('interval', 1),
            end_date=data.get('end_date'),
            days_of_week=data.get('days_of_week')
        )
        
        # Generate instances
        task = db.get_task(task_id)
        instances = task_manager.generate_recurring_instances(
            task['recurring_pattern_id'],
            data.get('num_instances', 10)
        )
        
        return jsonify({
            'task_id': task_id,
            'instances_generated': len(instances)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/recurring/<int:pattern_id>/generate', methods=['POST'])
def generate_recurring_instances(pattern_id):
    """Generate instances for recurring pattern"""
    try:
        data = request.json
        num = data.get('num_instances', 10)
        instances = task_manager.generate_recurring_instances(pattern_id, num)
        return jsonify({
            'generated': len(instances),
            'instance_ids': instances
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== DEPENDENCY ENDPOINTS ====================

@app.route('/api/dependencies', methods=['POST'])
def add_dependency():
    """Add task dependency"""
    try:
        data = request.json
        task_id = data.get('task_id')
        depends_on_id = data.get('depends_on_task_id')
        
        if task_manager.add_dependency(task_id, depends_on_id):
            return jsonify({'message': 'Dependency added'}), 201
        return jsonify({'error': 'Failed to add dependency'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dependencies/<int:task_id>/<int:depends_on_id>', methods=['DELETE'])
def remove_dependency(task_id, depends_on_id):
    """Remove task dependency"""
    try:
        if task_manager.remove_dependency(task_id, depends_on_id):
            return jsonify({'message': 'Dependency removed'})
        return jsonify({'error': 'Dependency not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dependencies/<int:task_id>', methods=['GET'])
def get_dependencies(task_id):
    """Get task dependencies"""
    try:
        dependencies = db.get_dependencies(task_id)
        return jsonify([dict(d) for d in dependencies])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dependents/<int:task_id>', methods=['GET'])
def get_dependents(task_id):
    """Get tasks that depend on this task"""
    try:
        dependents = db.get_dependents(task_id)
        return jsonify([dict(d) for d in dependents])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dependency-tree/<int:task_id>', methods=['GET'])
def get_dependency_tree(task_id):
    """Get dependency tree for task"""
    try:
        tree = task_manager.get_dependency_tree(task_id)
        return jsonify(tree)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== TIME TRACKING ENDPOINTS ====================

@app.route('/api/timers/start/<int:task_id>', methods=['POST'])
def start_timer(task_id):
    """Start timer for task"""
    try:
        log_id = time_tracker.start_timer(task_id)
        if log_id > 0:
            return jsonify({'log_id': log_id, 'message': 'Timer started'}), 201
        return jsonify({'error': 'Failed to start timer'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/timers/stop/<int:task_id>', methods=['POST'])
def stop_timer(task_id):
    """Stop timer for task"""
    try:
        success = time_tracker.stop_timer(task_id)
        if success:
            return jsonify({'message': 'Timer stopped'}), 200
        return jsonify({'message': 'No active timer found'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/timers/active', methods=['GET'])
def get_active_timers():
    """Get all active timers"""
    try:
        timers = time_tracker.get_active_timers()
        return jsonify([dict(t) for t in timers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/time-logs', methods=['GET'])
def get_all_time_logs():
    """Get all time logs"""
    try:
        # Get all time logs with task details
        query = """
            SELECT tl.id, tl.task_id, tl.start_time, tl.end_time, tl.duration_minutes, tl.notes, t.title as task_title
            FROM time_logs tl
            INNER JOIN tasks t ON tl.task_id = t.id
            ORDER BY tl.start_time DESC
        """
        logs = []
        for row in db.execute_query(query):
            log_dict = dict(row)
            # Ensure duration_minutes is never None
            if log_dict.get('duration_minutes') is None:
                log_dict['duration_minutes'] = 0
            logs.append(log_dict)
        return jsonify(logs)
    except Exception as e:
        print(f"Error in get_all_time_logs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@app.route('/api/time-logs/<int:task_id>', methods=['GET'])
def get_time_logs(task_id):
    """Get time logs for task"""
    try:
        logs = time_tracker.get_time_logs(task_id)
        return jsonify([dict(l) for l in logs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/time-logs/<int:task_id>', methods=['POST'])
def add_time_log(task_id):
    """Add manual time log"""
    try:
        data = request.json
        duration = data.get('duration_minutes')
        date_str = data.get('date')
        notes = data.get('notes')
        
        log_id = time_tracker.add_manual_time_log(task_id, duration, date_str, notes)
        return jsonify({'log_id': log_id, 'message': 'Time log added'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>/total-time', methods=['GET'])
def get_total_task_time(task_id):
    """Get total time spent on task"""
    try:
        minutes = time_tracker.get_task_total_time(task_id)
        hours = minutes / 60
        return jsonify({
            'task_id': task_id,
            'total_minutes': minutes,
            'total_hours': round(hours, 2),
            'formatted': f"{minutes // 60}h {minutes % 60}m"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ANALYTICS ENDPOINTS ====================

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard():
    """Get productivity dashboard"""
    try:
        dashboard = analytics.get_productivity_dashboard()
        return jsonify(dashboard)
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@app.route('/api/analytics/today', methods=['GET'])
def get_today_stats():
    """Get today's statistics"""
    try:
        stats = analytics.get_today_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/weekly', methods=['GET'])
def get_weekly_stats():
    """Get weekly statistics"""
    try:
        stats = analytics.get_weekly_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/monthly', methods=['GET'])
def get_monthly_stats():
    """Get monthly statistics"""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        stats = analytics.get_monthly_stats(year, month)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/completion-rate', methods=['GET'])
def get_completion_rate():
    """Get completion rate"""
    try:
        rate = analytics.get_completion_rate()
        return jsonify(rate)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/priority-rates', methods=['GET'])
def get_priority_completion_rates():
    """Get completion rates by priority"""
    try:
        rates = analytics.get_priority_completion_rate()
        return jsonify(rates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/task-counts', methods=['GET'])
def get_task_counts():
    """Get task counts by status and priority"""
    try:
        status_counts = analytics.get_task_counts_by_status()
        priority_counts = analytics.get_task_counts_by_priority()
        return jsonify({
            'by_status': status_counts,
            'by_priority': priority_counts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/trend', methods=['GET'])
def get_completion_trend():
    """Get completion trend"""
    try:
        days = request.args.get('days', 7, type=int)
        trend = analytics.get_completion_trend(days)
        return jsonify(trend)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/priority-analysis', methods=['GET'])
def get_priority_analysis():
    """Get detailed priority analysis"""
    try:
        analysis = analytics.get_priority_analysis()
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/time-breakdown/priority', methods=['GET'])
def get_time_breakdown_priority():
    """Get time breakdown by priority"""
    try:
        breakdown = time_tracker.get_time_breakdown_by_priority()
        return jsonify(breakdown)
    except Exception as e:
        print(f"Error in time breakdown by priority: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@app.route('/api/analytics/time-breakdown/status', methods=['GET'])
def get_time_breakdown_status():
    """Get time breakdown by status"""
    try:
        breakdown = time_tracker.get_time_breakdown_by_status()
        return jsonify(breakdown)
    except Exception as e:
        print(f"Error in time breakdown by status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@app.route('/api/analytics/time-by-task', methods=['GET'])
def get_time_by_task():
    """Get time spent on each task"""
    try:
        tasks = time_tracker.get_time_by_task()
        return jsonify([dict(t) for t in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ==================== SERVICE ACCOUNT CALENDAR SYNC ENDPOINTS ====================

@app.route('/api/calendar/service-account/status', methods=['GET'])
def service_account_status():
    """Get Service Account calendar sync status"""
    try:
        status = service_account_sync.get_sync_status()
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/sync-task/<int:task_id>', methods=['POST'])
def service_account_sync_task(task_id):
    """Sync a single task to calendar via Service Account"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar. Make sure service_account_key.json is in the project folder.'
            }), 401
        
        success, message = service_account_sync.sync_task(task_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'task_id': task_id
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/sync-all', methods=['POST'])
def service_account_sync_all():
    """Sync all tasks to calendar via Service Account"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar. Make sure service_account_key.json is in the project folder.'
            }), 401
        
        user_id = session.get('user_id')
        
        results = service_account_sync.sync_all_tasks(user_id=user_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Sync completed',
            'data': results
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/create-event/<int:task_id>', methods=['POST'])
def service_account_create_event(task_id):
    """Create calendar event for task via Service Account"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar'
            }), 401
        
        success, message = service_account_sync.create_event(task_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'task_id': task_id
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/update-event/<int:task_id>', methods=['POST'])
def service_account_update_event(task_id):
    """Update calendar event for task via Service Account"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar'
            }), 401
        
        success, message = service_account_sync.update_event(task_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'task_id': task_id
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/delete-event/<int:task_id>', methods=['POST'])
def service_account_delete_event(task_id):
    """Delete calendar event for task via Service Account"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar'
            }), 401
        
        success, message = service_account_sync.delete_event(task_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'task_id': task_id
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/calendars', methods=['GET'])
def service_account_list_calendars():
    """List available calendars"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar'
            }), 401
        
        calendars = service_account_sync.list_calendars()
        
        return jsonify({
            'status': 'success',
            'data': calendars
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calendar/service-account/events', methods=['GET'])
def service_account_list_events():
    """Get calendar events"""
    try:
        if not service_account_sync.is_authenticated():
            return jsonify({
                'status': 'error',
                'message': 'Not authenticated with Google Calendar'
            }), 401
        
        max_results = request.args.get('max_results', 10, type=int)
        events = service_account_sync.get_calendar_events(max_results=max_results)
        
        return jsonify({
            'status': 'success',
            'data': events
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== CALENDAR EXPORT ENDPOINTS ====================

@app.route('/api/export/calendar/all', methods=['GET'])
def export_all_tasks_calendar():
    """Export all tasks to calendar"""
    try:
        filename = f"all_tasks_{datetime.now().strftime('%Y%m%d')}.ics"
        calendar_exporter.export_tasks_to_ics(filename)
        return send_file(filename, as_attachment=True, mimetype='text/calendar')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/calendar/undone', methods=['GET'])
def export_undone_tasks_calendar():
    """Export undone tasks to calendar"""
    try:
        filename = f"undone_tasks_{datetime.now().strftime('%Y%m%d')}.ics"
        calendar_exporter.export_undone_tasks(filename)
        return send_file(filename, as_attachment=True, mimetype='text/calendar')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/calendar/priority/<priority>', methods=['GET'])
def export_priority_tasks_calendar(priority):
    """Export tasks by priority to calendar"""
    try:
        filename = f"tasks_{priority}_{datetime.now().strftime('%Y%m%d')}.ics"
        calendar_exporter.export_priority_tasks(priority, filename)
        return send_file(filename, as_attachment=True, mimetype='text/calendar')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/calendar/overdue', methods=['GET'])
def export_overdue_tasks_calendar():
    """Export overdue tasks to calendar"""
    try:
        filename = f"overdue_tasks_{datetime.now().strftime('%Y%m%d')}.ics"
        calendar_exporter.export_overdue_tasks(filename)
        return send_file(filename, as_attachment=True, mimetype='text/calendar')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== DATABASE ENDPOINTS ====================

@app.route('/api/database/stats', methods=['GET'])
def get_database_stats():
    """Get database statistics"""
    try:
        stats = db.get_database_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/clear', methods=['POST'])
def clear_database():
    """Clear database (requires confirmation)"""
    try:
        confirm = request.json.get('confirm', False)
        if not confirm:
            return jsonify({'error': 'Confirmation required'}), 400
        
        db.clear_database()
        return jsonify({'message': 'Database cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({'error': 'Bad request'}), 400


# ==================== FRONTEND ROUTES ====================

@app.route('/login', methods=['GET'])
def login_page():
    """Serve login page"""
    try:
        return render_template('login.html')
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Login page not available: {str(e)}'}), 500


@app.route('/signup', methods=['GET'])
def signup_page():
    """Serve signup page"""
    try:
        return render_template('signup.html')
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Signup page not available: {str(e)}'}), 500


# ==================== DASHBOARD ROUTE ====================

@app.route('/', methods=['GET'])
def home():
    """Home page - redirect to signup if not authenticated, dashboard if authenticated"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            # Not logged in - show signup page
            return render_template('signup.html')
        else:
            # Logged in - show dashboard
            return render_template('index.html')
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Home page not available: {str(e)}'}), 500


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Serve the web dashboard"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            # Not logged in - redirect to signup
            from flask import redirect
            return redirect('/signup')
        return render_template('index.html')
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Dashboard not available: {str(e)}'}), 500


# ==================== GOOGLE CALENDAR SYNC ENDPOINTS ====================

@app.route('/api/calendar/authenticate', methods=['POST'])
def authenticate_google_calendar():
    """
    Authenticate with Google Calendar.
    Returns OAuth URL for user to visit and authorize
    """
    try:
        # Check if already authenticated
        if google_calendar_sync.service:
            return jsonify({
                'status': 'already_authenticated',
                'message': 'Already authenticated with Google Calendar'
            })
        
        # For now, return a simple message
        # User should navigate to Google Cloud OAuth dialog
        return jsonify({
            'status': 'ready_to_auth',
            'message': 'Ready to authenticate. Please call the proper auth endpoint.',
            'note': 'Use /api/calendar/oauth/init to start OAuth flow'
        })
    except Exception as e:
        import traceback
        print(f"Error in authenticate_google_calendar: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/calendar/auth/callback', methods=['GET'])
def auth_callback():
    """
    Handle OAuth callback from Google
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle
        
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        flow = InstalledAppFlow.from_client_secrets_file(
            'google_credentials.json',
            ['https://www.googleapis.com/auth/calendar']
        )
        
        # Exchange code for credentials
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save credentials
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        # Re-initialize the sync service
        google_calendar_sync.service = build('calendar', 'v3', credentials=creds)
        
        return jsonify({
            'status': 'authenticated',
            'message': 'Successfully authenticated with Google Calendar'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calendar/sync/create/<int:task_id>', methods=['POST'])
def sync_create_task(task_id):
    """
    Create a Google Calendar event for a specific task.
    Call this after creating a new task in the management system.
    """
    try:
        if not google_calendar_sync.service:
            return jsonify({'error': 'Not authenticated with Google Calendar'}), 401
        
        if google_calendar_sync.create_event(task_id):
            return jsonify({'message': f'Task {task_id} synced to Google Calendar'})
        else:
            return jsonify({'error': 'Failed to sync task'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calendar/sync/update/<int:task_id>', methods=['POST'])
def sync_update_task(task_id):
    """
    Update Google Calendar event when task is modified.
    Call this after updating a task.
    """
    try:
        if not google_calendar_sync.service:
            return jsonify({'error': 'Not authenticated with Google Calendar'}), 401
        
        if google_calendar_sync.update_event(task_id):
            return jsonify({'message': f'Task {task_id} updated in Google Calendar'})
        else:
            return jsonify({'error': 'Failed to update task'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calendar/sync/delete/<int:task_id>', methods=['POST'])
def sync_delete_task(task_id):
    """
    Delete Google Calendar event when task is deleted.
    Call this after deleting a task.
    """
    try:
        if not google_calendar_sync.service:
            return jsonify({'error': 'Not authenticated with Google Calendar'}), 401
        
        if google_calendar_sync.delete_event(task_id):
            return jsonify({'message': f'Task {task_id} removed from Google Calendar'})
        else:
            return jsonify({'error': 'Failed to delete task'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calendar/sync/all', methods=['POST'])
def sync_all_tasks():
    """
    Full synchronization: Sync all tasks with Google Calendar.
    Use this for first-time setup to sync existing tasks.
    """
    try:
        if not google_calendar_sync.service:
            return jsonify({'error': 'Not authenticated with Google Calendar'}), 401
        
        results = google_calendar_sync.sync_all()
        return jsonify({
            'status': 'success',
            'message': 'Full sync completed',
            'created': results['created'],
            'updated': results['updated'],
            'deleted': results['deleted']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calendar/sync/status', methods=['GET'])
def sync_status():
    """Get synchronization status and mapping information."""
    try:
        is_authenticated = google_calendar_sync.service is not None
        task_count = len(google_calendar_sync.task_event_map)
        
        return jsonify({
            'authenticated': is_authenticated,
            'synced_tasks': task_count,
            'service_status': 'connected' if is_authenticated else 'disconnected'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("TASK MANAGEMENT SYSTEM - FLASK API".center(70))
    print("=" * 70)
    print("\n[OK] Starting Flask API server...")
    print("[OK] API available at: http://localhost:5000")
    print("[OK] Dashboard available at: http://localhost:5000/dashboard")
    print("[OK] Google Calendar Sync available at: /api/calendar/*")
    print("\n" + "=" * 70 + "\n")
    
    app.run(debug=False, port=5000, host='0.0.0.0', use_reloader=False)
