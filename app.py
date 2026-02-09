from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import sqlite3
import os
import base64

app = Flask(__name__)
app.config['DATABASE'] = 'projects.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize the database with tables"""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            icon_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_task_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_task_id) REFERENCES tasks (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            author TEXT DEFAULT 'User',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    db.close()

@app.route('/')
def index():
    """Display all projects"""
    db = get_db()
    projects = db.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('index.html', projects=projects)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Display project details with tasks and subtasks"""
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        db.close()
        return redirect(url_for('index'))
    
    # Get all tasks for this project
    tasks = db.execute('''
        SELECT * FROM tasks 
        WHERE project_id = ? AND parent_task_id IS NULL 
        ORDER BY created_at DESC
    ''', (project_id,)).fetchall()
    
    # Get project comments
    project_comments = db.execute('''
        SELECT * FROM comments 
        WHERE entity_type = 'project' AND entity_id = ? 
        ORDER BY created_at DESC
    ''', (project_id,)).fetchall()
    
    db.close()
    return render_template('project_detail.html', 
                         project=project, 
                         tasks=tasks,
                         project_comments=project_comments)

@app.route('/project/add', methods=['POST'])
def add_project():
    """Add a new project"""
    name = request.form.get('name')
    description = request.form.get('description', '')
    icon_data = None
    
    # Handle icon upload
    if 'icon' in request.files:
        icon_file = request.files['icon']
        if icon_file and icon_file.filename:
            # Read the file and convert to base64
            icon_bytes = icon_file.read()
            icon_data = base64.b64encode(icon_bytes).decode('utf-8')
    
    if name:
        db = get_db()
        db.execute('INSERT INTO projects (name, description, icon_data) VALUES (?, ?, ?)', 
                  (name, description, icon_data))
        db.commit()
        db.close()
    
    return redirect(url_for('index'))

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project only if it has no tasks"""
    db = get_db()
    
    # Check if project has any tasks
    task_count = db.execute('SELECT COUNT(*) as count FROM tasks WHERE project_id = ?', 
                           (project_id,)).fetchone()
    
    if task_count['count'] > 0:
        db.close()
        # Return error - could be improved with flash messages
        return redirect(url_for('index'))
    
    # Delete project if no tasks
    db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    db.commit()
    db.close()
    return redirect(url_for('index'))

@app.route('/project/<int:project_id>/task-count')
def get_task_count(project_id):
    """Get task count for a project"""
    db = get_db()
    result = db.execute('SELECT COUNT(*) as count FROM tasks WHERE project_id = ?', 
                       (project_id,)).fetchone()
    db.close()
    return jsonify({'count': result['count']})

@app.route('/task/add', methods=['POST'])
def add_task():
    """Add a new task or subtask"""
    project_id = request.form.get('project_id', type=int)
    parent_task_id = request.form.get('parent_task_id', type=int)
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if name and project_id:
        db = get_db()
        db.execute('''
            INSERT INTO tasks (project_id, parent_task_id, name, description) 
            VALUES (?, ?, ?, ?)
        ''', (project_id, parent_task_id if parent_task_id else None, name, description))
        db.commit()
        db.close()
    
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/task/<int:task_id>/subtasks')
def get_subtasks(task_id):
    """Get subtasks for a task (AJAX endpoint)"""
    db = get_db()
    subtasks = db.execute('''
        SELECT * FROM tasks 
        WHERE parent_task_id = ? 
        ORDER BY created_at DESC
    ''', (task_id,)).fetchall()
    
    comments = db.execute('''
        SELECT * FROM comments 
        WHERE entity_type = 'task' AND entity_id = ? 
        ORDER BY created_at DESC
    ''', (task_id,)).fetchall()
    
    db.close()
    
    return jsonify({
        'subtasks': [dict(row) for row in subtasks],
        'comments': [dict(row) for row in comments]
    })

@app.route('/task/<int:task_id>/update-status', methods=['POST'])
def update_task_status(task_id):
    """Update task status"""
    status = request.form.get('status')
    
    if status in ['pending', 'in_progress', 'completed']:
        db = get_db()
        db.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """Delete a task"""
    db = get_db()
    task = db.execute('SELECT project_id FROM tasks WHERE id = ?', (task_id,)).fetchone()
    project_id = task['project_id'] if task else None
    
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    db.close()
    
    if project_id:
        return redirect(url_for('project_detail', project_id=project_id))
    return redirect(url_for('index'))

@app.route('/comment/add', methods=['POST'])
def add_comment():
    """Add a comment to a project or task"""
    entity_type = request.form.get('entity_type')
    entity_id = request.form.get('entity_id', type=int)
    content = request.form.get('content')
    author = request.form.get('author', 'User')
    
    if entity_type in ['project', 'task'] and entity_id and content:
        db = get_db()
        db.execute('''
            INSERT INTO comments (entity_type, entity_id, content, author) 
            VALUES (?, ?, ?, ?)
        ''', (entity_type, entity_id, content, author))
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
