// Task Management System - Web Dashboard
// Main JavaScript Application

const API_BASE = 'http://localhost:5000';

// ============================================================================
// DOM Elements
// ============================================================================

const navLinks = document.querySelectorAll('.nav-link');
const pageContents = document.querySelectorAll('.page-content');
const currentTimeEl = document.getElementById('current-time');
const taskModal = document.getElementById('taskModal');
const taskForm = document.getElementById('taskForm');
const toastContainer = document.getElementById('toast');

// ============================================================================
// State Management
// ============================================================================

const state = {
    tasks: [],
    currentPage: 'dashboard',
    activeFilter: 'all',
    editingTaskId: null,
    activeTimers: {},
    timerIntervals: {}
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    setupNavigation();
    setupEventListeners();
    loadDashboard();
    updateTime();
    setInterval(updateTime, 1000);
    setInterval(updateActiveTimers, 1000);
    checkHealth();
}

// ============================================================================
// Navigation & Page Management
// ============================================================================

function setupNavigation() {
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            goToPage(page);
        });
    });
}

function goToPage(page) {
    // Hide all pages
    pageContents.forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all nav links
    navLinks.forEach(link => {
        link.classList.remove('active');
    });

    // Show selected page
    const selectedPage = document.getElementById(`${page}Page`);
    if (selectedPage) {
        selectedPage.classList.add('active');
    }

    // Set active nav link
    const activeLink = document.querySelector(`[data-page="${page}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    state.currentPage = page;

    // Load page-specific data
    switch (page) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'tasks':
            loadTasks();
            break;
        case 'time':
            loadTimeTracking();
            break;
        case 'analytics':
            loadAnalytics();
            break;
        case 'settings':
            loadSettings();
            break;
    }
}

// ============================================================================
// Event Listeners Setup
// ============================================================================

function setupEventListeners() {
    // Task Form
    const createTaskBtn = document.getElementById('btn-new-task');
    if (createTaskBtn) {
        createTaskBtn.addEventListener('click', openTaskModal);
    }

    // Task Modal
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeTaskModal);
    }

    const closeModalBtn = document.getElementById('closeModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeTaskModal);
    }

    window.addEventListener('click', (e) => {
        if (e.target === taskModal) {
            closeTaskModal();
        }
    });

    if (taskForm) {
        taskForm.addEventListener('submit', handleTaskSubmit);
    }

    // Task Filters
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.activeFilter = btn.dataset.filter;
            loadTasks();
        });
    });

    // Export Buttons
    const exportAllBtn = document.getElementById('exportAll');
    if (exportAllBtn) {
        exportAllBtn.addEventListener('click', () => exportCalendar('all'));
    }

    const exportUndoneBtn = document.getElementById('exportUndone');
    if (exportUndoneBtn) {
        exportUndoneBtn.addEventListener('click', () => exportCalendar('undone'));
    }

    const exportOverdueBtn = document.getElementById('exportOverdue');
    if (exportOverdueBtn) {
        exportOverdueBtn.addEventListener('click', () => exportCalendar('overdue'));
    }
}

// ============================================================================
// API Calls
// ============================================================================

async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`API Error on ${endpoint}:`, response.status, errorBody);
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        // Handle file downloads (for ICS files)
        if (response.headers.get('content-type') && response.headers.get('content-type').includes('text/calendar')) {
            return await response.text();
        }

        // Handle other responses
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }

        return response;
    } catch (error) {
        console.error(`API Error on ${endpoint}:`, error);
        throw error;
    }
}

async function checkHealth() {
    try {
        await apiCall('/api/health');
    } catch (error) {
        console.log('Health check failed (non-critical)');
    }
}

// ============================================================================
// Dashboard Page
// ============================================================================

async function loadDashboard() {
    try {
        const tasks = await apiCall('/api/tasks');

        state.tasks = tasks;

        // Update stat cards
        const totalTasks = tasks.length;
        const completedTasks = tasks.filter(t => t.status === 'done').length;
        const completionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
        const overdueTasks = tasks.filter(t => t.due_date && new Date(t.due_date) < new Date() && t.status !== 'done').length;

        document.getElementById('totalTasks').textContent = totalTasks;
        document.getElementById('completedTasks').textContent = completedTasks;
        document.getElementById('completionRate').textContent = completionRate + '%';
        document.getElementById('overdueTasks').textContent = overdueTasks;

        // Update quick stats
        const quickStatsList = document.getElementById('quickStatsList');
        quickStatsList.innerHTML = `
            <div class="stat-row">
                <span>High Priority Tasks</span>
                <span>${tasks.filter(t => t.priority === 'high' && t.status !== 'done').length}</span>
            </div>
            <div class="stat-row">
                <span>In Progress</span>
                <span>${tasks.filter(t => t.status === 'in_progress').length}</span>
            </div>
            <div class="stat-row">
                <span>Blocked Tasks</span>
                <span>${tasks.filter(t => t.status === 'blocked').length}</span>
            </div>
            <div class="stat-row">
                <span>Today's Tasks</span>
                <span>${tasks.filter(t => {
                    const due = new Date(t.due_date);
                    const today = new Date();
                    return due.toDateString() === today.toDateString();
                }).length}</span>
            </div>
        `;

        // Update recent tasks
        const recentTasksList = document.getElementById('recentTasksList');
        const recentTasks = tasks
            .filter(t => t.status !== 'done')
            .slice(0, 5);

        recentTasksList.innerHTML = recentTasks.map(task => `
            <div class="task-mini-item ${task.priority}">
                <span>${task.title}</span>
                <span style="font-size: 0.75rem; color: var(--text-secondary);">${task.priority}</span>
            </div>
        `).join('') || '<div class="empty">No active tasks</div>';

    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// ============================================================================
// Tasks Page
// ============================================================================

async function loadTasks() {
    try {
        let tasks = await apiCall('/api/tasks');

        // Apply filter
        switch (state.activeFilter) {
            case 'not_started':
                tasks = tasks.filter(t => t.status === 'not_started');
                break;
            case 'in_progress':
                tasks = tasks.filter(t => t.status === 'in_progress');
                break;
            case 'done':
                tasks = tasks.filter(t => t.status === 'done');
                break;
            case 'blocked':
                tasks = tasks.filter(t => t.status === 'blocked');
                break;
        }

        state.tasks = tasks;

        const tasksList = document.getElementById('tasksList');
        tasksList.innerHTML = tasks.map(task => `
            <div class="task-item ${task.priority} ${task.status === 'done' ? 'done' : ''}">
                <div class="task-content">
                    <div class="task-title">${task.title}</div>
                    <div class="task-meta">
                        Status: ${task.status} | Priority: ${task.priority}
                        ${task.due_date ? ` | Due: ${new Date(task.due_date).toLocaleDateString()}` : ''}
                    </div>
                </div>
                <div class="task-actions">
                    ${task.status !== 'done' ? `
                        <button class="task-btn ${task.status === 'in_progress' ? 'active' : ''}" id="start-btn-${task.id}" onclick="updateTaskStatus(${task.id}, 'in_progress')">${task.status === 'in_progress' ? 'Started' : 'Start'}</button>
                    ` : ''}
                    ${task.status !== 'done' ? `
                        <button class="task-btn" onclick="updateTaskStatus(${task.id}, 'done')">Done</button>
                    ` : ''}
                    <button class="task-btn" onclick="editTask(${task.id})">Edit</button>
                    <button class="task-btn danger" onclick="deleteTask(${task.id})">Delete</button>
                </div>
            </div>
        `).join('') || '<div class="empty">No tasks found</div>';

    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

async function updateTaskStatus(taskId, newStatus) {
    try {
        // Update button text immediately for better UX
        if (newStatus === 'in_progress') {
            const startBtn = document.getElementById(`start-btn-${taskId}`);
            if (startBtn) {
                startBtn.textContent = 'Started';
                startBtn.classList.add('active');
            }
        }

        await apiCall(`/api/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify({ status: newStatus })
        });

        showToast(`Task status updated to ${newStatus}`, 'success');

        if (newStatus === 'in_progress') {
            setTimeout(() => startTimer(taskId), 200);
        }

        if (newStatus === 'done') {
            setTimeout(async () => {
                await stopTimerByTask(taskId);
                showToast('⏹️ Timer stopped because task is Done', 'success');
            }, 200);
        }

        loadTasks();
        loadDashboard();

    } catch (error) {
        console.error('Error updating task:', error);
    }
}

async function editTask(taskId) {
    const task = state.tasks.find(t => t.id === taskId);
    if (task) {
        state.editingTaskId = taskId;
        document.getElementById('taskTitle').value = task.title;
        document.getElementById('taskDescription').value = task.description || '';
        document.getElementById('taskPriority').value = task.priority;
        document.getElementById('taskDueDate').value = task.due_date ? task.due_date.split('T')[0] : '';
        document.getElementById('taskStatus').value = task.status;
        openTaskModal();
    }
}

async function deleteTask(taskId) {
    if (confirm('Are you sure you want to delete this task?')) {
        try {
            await apiCall(`/api/tasks/${taskId}`, { method: 'DELETE' });
            showToast('Task deleted successfully', 'success');
            loadTasks();
        } catch (error) {
            console.error('Error deleting task:', error);
        }
    }
}

async function handleTaskSubmit(e) {
    e.preventDefault();

    const taskData = {
        title: document.getElementById('taskTitle').value,
        description: document.getElementById('taskDescription').value,
        priority: document.getElementById('taskPriority').value,
        due_date: document.getElementById('taskDueDate').value,
        status: document.getElementById('taskStatus')?.value || 'not_started'
    };

    try {
        if (state.editingTaskId) {
            await apiCall(`/api/tasks/${state.editingTaskId}`, {
                method: 'PUT',
                body: JSON.stringify(taskData)
            });
            showToast('Task updated successfully', 'success');
        } else {
            await apiCall('/api/tasks', {
                method: 'POST',
                body: JSON.stringify(taskData)
            });
            showToast('Task created successfully', 'success');
        }

        taskForm.reset();
        closeTaskModal();
        loadTasks();
        loadDashboard();
        loadTimeTracking();

    } catch (error) {
        console.error('Error saving task:', error);
    }
}

function openTaskModal() {
    if (!state.editingTaskId) {
        taskForm.reset();
        document.getElementById('taskFormTitle').textContent = 'Create New Task';
    } else {
        document.getElementById('taskFormTitle').textContent = 'Edit Task';
    }
    taskModal.classList.add('show');
}

function closeTaskModal() {
    taskModal.classList.remove('show');
    taskForm.reset();
    state.editingTaskId = null;
}

// ============================================================================
// Time Tracking Page
// ============================================================================

async function loadTimeTracking() {
    try {
        const [activeTimers, priorityBreakdown, statusBreakdown, logs] = await Promise.all([
            apiCall('/api/timers/active'),
            apiCall('/api/analytics/time-breakdown/priority'),
            apiCall('/api/analytics/time-breakdown/status'),
            apiCall('/api/time-logs')
        ]);

        // Store active timers in state for continuous updates
        state.activeTimers = {};
        activeTimers.forEach(timer => {
            state.activeTimers[timer.id] = timer;
        });

        // ✅ Active timers list (Stop button REMOVED)
        const timersList = document.getElementById('activeTimersList');
        timersList.innerHTML = activeTimers.length > 0
            ? activeTimers.map(timer => {
                const startTime = new Date(timer.start_time);
                const elapsedSeconds = Math.floor((new Date() - startTime) / 1000);

                return `
                <div class="timer-item">
                    <div class="timer-timer-title">${timer.title}</div>
                    <div class="timer-elapsed" id="timer-${timer.id}">
                        ${formatDuration(elapsedSeconds)}
                    </div>
                </div>
            `;
            }).join('')
            : '<div class="empty">No active timers</div>';

        // Update time breakdown
        const priorityBreakdownDiv = document.getElementById('priorityBreakdown');
        const statusBreakdownDiv = document.getElementById('statusBreakdown');
        const priorities = ['high', 'medium', 'low'];
        const statuses = ['not_started', 'in_progress', 'done', 'blocked'];

        // By priority
        let priorityHTML = '';
        priorities.forEach(priority => {
            const priorityData = priorityBreakdown[priority];
            const minutes = priorityData ? Math.round(priorityData.minutes) : 0;
            priorityHTML += `
                <div class="breakdown-item">
                    <span>${priority}</span>
                    <span>${minutes} min</span>
                </div>
            `;
        });
        priorityBreakdownDiv.innerHTML = priorityHTML;

        // By status
        let statusHTML = '';
        statuses.forEach(status => {
            const statusData = statusBreakdown[status];
            const minutes = statusData ? Math.round(statusData.minutes) : 0;
            statusHTML += `
                <div class="breakdown-item">
                    <span>${status}</span>
                    <span>${minutes} min</span>
                </div>
            `;
        });
        statusBreakdownDiv.innerHTML = statusHTML;

        // Update time logs (last 10)
        const logsList = document.getElementById('timeLogsList');
        const recentLogs = logs.slice(-10).reverse();
        logsList.innerHTML = recentLogs.length > 0
            ? recentLogs.map(log => {
                const durationMinutes = log.duration_minutes || 0;
                return `
                <div class="breakdown-item">
                    <span>${log.task_title}</span>
                    <span>${durationMinutes} min</span>
                </div>
            `;
            }).join('')
            : '<div class="empty">No time logs</div>';

    } catch (error) {
        console.error('Error loading time tracking:', error);
    }
}

async function startTimer(taskId) {
    try {
        const response = await apiCall(`/api/timers/start/${taskId}`, { method: 'POST' });
        if (response.log_id) {
            showToast('⏱️ Timer started', 'success');
            setTimeout(() => loadTimeTracking(), 500);
        }
    } catch (error) {
        console.error('Error starting timer:', error);
        showToast('❌ Failed to start timer', 'error');
    }
}

// ✅ Stop timer by looking up active log id for task
async function stopTimerByTask(taskId) {
    try {
        // ✅ Backend expects TASK ID
        await apiCall(`/api/timers/stop/${taskId}`, { method: 'POST' });

        // ✅ After stopping timer, reload active timers fresh
        await loadTimeTracking();

    } catch (error) {
        console.error("Error stopping timer by task:", error);
    }
}



// ✅ stopTimer(taskId, updateStatus=true)
async function stopTimer(taskId, updateStatus = true) {
    try {
        await stopTimerByTask(taskId);
        showToast('⏹️ Timer stopped', 'success');

        if (updateStatus) {
            await apiCall(`/api/tasks/${taskId}`, {
                method: 'PUT',
                body: JSON.stringify({ status: 'done' })
            });
            showToast('✅ Task marked as Done', 'success');
        }

        loadTasks();
        loadDashboard();
        loadTimeTracking();

    } catch (error) {
        console.error('Error stopping timer:', error);
    }
}

async function updateActiveTimers() {
    try {
        // ✅ Fetch fresh active timers
        const activeTimers = await apiCall('/api/timers/active');

        // ✅ Reset state completely (removes stopped ones)
        state.activeTimers = {};
        activeTimers.forEach(timer => {
            state.activeTimers[timer.id] = timer;
        });

        // ✅ Update UI timers display
        Object.keys(state.activeTimers).forEach(timerId => {
            const timerEl = document.getElementById(`timer-${timerId}`);
            const timer = state.activeTimers[timerId];

            if (timerEl && timer.start_time) {
                const startTime = new Date(timer.start_time);
                const elapsedSeconds = Math.floor((new Date() - startTime) / 1000);
                timerEl.textContent = formatDuration(elapsedSeconds);
            }
        });

    } catch (error) {
        console.log("Active timer refresh failed (non critical)");
    }
}


// ============================================================================
// Analytics Page
// ============================================================================

async function loadAnalytics() {
    try {
        const analytics = await apiCall('/api/analytics/dashboard');

        const priorityAnalysis = document.getElementById('priorityAnalysis');
        const priorityCompletion = analytics.priority_completion || {};
        const priorityHTML = `
            <div class="analysis-row analysis-row-header">
                <span>Priority</span>
                <span>Total</span>
                <span>Done</span>
                <span>%</span>
                <span></span>
            </div>
            ${['high', 'medium', 'low'].map(priority => {
                const data = priorityCompletion[priority] || {};
                const total = data.total || 0;
                const done = data.done || 0;
                const percent = total > 0 ? Math.round((done / total) * 100) : 0;
                return `
                    <div class="analysis-row">
                        <span style="text-transform: capitalize; font-weight: 600;">${priority}</span>
                        <span>${total}</span>
                        <span>${done}</span>
                        <span>${percent}%</span>
                        <div class="progress-bar">
                            <div class="progress-bar-fill" style="width: ${percent}%"></div>
                        </div>
                    </div>
                `;
            }).join('')}
        `;
        priorityAnalysis.innerHTML = priorityHTML;

        const trendsHTML = document.getElementById('trendChart');
        const weeklyData = analytics.weekly || {};
        let trendContent = '<div class="trend-chart">';

        Object.entries(weeklyData).forEach(([date, data]) => {
            const count = data?.tasks_completed || 0;
            const bars = Array(Math.min(count, 20)).fill('█').join('');
            trendContent += `
                <div class="trend-bar">
                    <div class="trend-date">${date}</div>
                    <div class="trend-bars">${bars}</div>
                    <div class="trend-count">${count}</div>
                </div>
            `;
        });
        trendContent += '</div>';

        trendsHTML.innerHTML = trendContent;

    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

// ============================================================================
// Settings Page
// ============================================================================

async function loadSettings() {
    try {
        const stats = await apiCall('/api/database/stats');
        const tasks = await apiCall('/api/tasks');

        // Calculate database stats from tasks
        const totalTasks = tasks.length;
        const completedTasks = tasks.filter(t => t.status === 'done').length;
        const allTimeLogs = tasks.reduce((sum, task) => sum + (task.time_logged || 0), 0);

        const statsEl = document.getElementById('dbStats');
        statsEl.innerHTML = `
            <div class="db-row">
                <strong>Total Tasks</strong>
                <span>${totalTasks}</span>
            </div>
            <div class="db-row">
                <strong>Completed Tasks</strong>
                <span>${completedTasks}</span>
            </div>
            <div class="db-row">
                <strong>Total Time Logged</strong>
                <span>${formatDuration(allTimeLogs)}</span>
            </div>
            <div class="db-row">
                <strong>Database Size</strong>
                <span>N/A</span>
            </div>
            <div class="db-row" style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 10px;">
                <em>Tasks Table: ${stats.tasks || 0} rows | Time Logs: ${stats.time_logs || 0} rows</em>
            </div>
        `;
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function exportCalendar(type = 'all') {
    try {
        const endpoint = `/api/export/calendar/${type}`;
        const ics = await apiCall(endpoint);

        const blob = new Blob([ics], { type: 'text/calendar' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tasks-${type}-${new Date().toISOString().split('T')[0]}.ics`;
        a.click();
        window.URL.revokeObjectURL(url);

        showToast(`Exported ${type} tasks successfully`, 'success');
    } catch (error) {
        console.error('Error exporting calendar:', error);
        showToast(`Error exporting ${type} tasks`, 'error');
    }
}

async function clearDatabase() {
    if (confirm('Are you sure you want to clear all data? This cannot be undone!')) {
        try {
            await apiCall('/api/database/clear', { method: 'POST' });
            showToast('Database cleared', 'success');
            goToPage('dashboard');
        } catch (error) {
            console.error('Error clearing database:', error);
        }
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const dateString = now.toLocaleDateString();
    if (currentTimeEl) {
        currentTimeEl.textContent = `${dateString} ${timeString}`;
    }
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// ============================================================================
// Export for use in other files
// ============================================================================

window.app = {
    goToPage,
    updateTaskStatus,
    editTask,
    deleteTask,
    startTimer,
    stopTimer,
    exportCalendar,
    clearDatabase
};
