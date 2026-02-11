from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import sqlite3
import os
import base64
import markdown
import re

app = Flask(__name__)

# Ensure data directory exists
DATA_DIR = '/app/data' if os.path.exists('/app') else './data'
os.makedirs(DATA_DIR, exist_ok=True)

app.config['DATABASE'] = os.path.join(DATA_DIR, 'projects.db')

# Add markdown filter to Jinja
@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown text to HTML with links opening in new tabs"""
    if not text:
        return ''
    html = markdown.markdown(
        text,
        extensions=['fenced_code', 'tables', 'sane_lists'],
        output_format='html5'
    )
    # Add target="_blank" to all links
    html = re.sub(r'<a href="', r'<a target="_blank" rel="noopener noreferrer" href="', html)
    return html

@app.template_filter('strip_markdown')
def strip_markdown_filter(text):
    """Strip markdown formatting for plain text preview"""
    if not text:
        return ''
    import re
    # Remove markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.+?)`', r'\1', text)        # Code
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # Headers
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)  # Lists
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # Numbered lists
    text = re.sub(r'\n', ' ', text)  # Newlines to spaces
    return text.strip()

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
    
    # Get task statistics for each project (parent tasks only, not subtasks)
    project_stats = {}
    for project in projects:
        stats = db.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM tasks 
            WHERE project_id = ? AND parent_task_id IS NULL
        ''', (project['id'],)).fetchone()
        project_stats[project['id']] = stats
    
    db.close()
    return render_template('index.html', projects=projects, project_stats=project_stats)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Display project details with tasks and subtasks"""
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        db.close()
        return redirect(url_for('index'))
    
    # Get all tasks for this project, ordered by status (completed last)
    tasks = db.execute('''
        SELECT * FROM tasks 
        WHERE project_id = ? AND parent_task_id IS NULL 
        ORDER BY 
            CASE status 
                WHEN 'pending' THEN 1 
                WHEN 'in_progress' THEN 2 
                WHEN 'completed' THEN 3 
            END,
            created_at DESC
    ''', (project_id,)).fetchall()
    
    # Get subtasks for each task
    task_subtasks = {}
    task_progress = {}
    for task in tasks:
        subtasks = db.execute('''
            SELECT * FROM tasks 
            WHERE parent_task_id = ? 
            ORDER BY created_at DESC
        ''', (task['id'],)).fetchall()
        task_subtasks[task['id']] = subtasks
        
        # Calculate progress based on subtasks
        if subtasks:
            total_progress = 0
            for subtask in subtasks:
                if subtask['status'] == 'pending':
                    total_progress += 0
                elif subtask['status'] == 'in_progress':
                    total_progress += 50
                elif subtask['status'] == 'completed':
                    total_progress += 100
            task_progress[task['id']] = int(total_progress / len(subtasks))
        else:
            task_progress[task['id']] = None
    
    # Get last comment info for each task (with time)
    task_last_comments = {}
    for task in tasks:
        last_comment = db.execute('''
            SELECT * FROM comments 
            WHERE entity_type = 'task' AND entity_id = ? 
            ORDER BY created_at DESC LIMIT 1
        ''', (task['id'],)).fetchone()
        if last_comment:
            task_last_comments[task['id']] = last_comment
    
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
                         task_subtasks=task_subtasks,
                         task_progress=task_progress,
                         task_last_comments=task_last_comments,
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

@app.route('/project/<int:project_id>/update', methods=['POST'])
def update_project(project_id):
    """Update project details"""
    name = request.form.get('name')
    description = request.form.get('description', '')
    icon_data = None
    
    if name:
        db = get_db()
        
        # Handle new icon upload if provided
        if 'icon' in request.files:
            icon_file = request.files['icon']
            if icon_file and icon_file.filename:
                icon_bytes = icon_file.read()
                icon_data = base64.b64encode(icon_bytes).decode('utf-8')
                db.execute('UPDATE projects SET name = ?, description = ?, icon_data = ? WHERE id = ?', 
                          (name, description, icon_data, project_id))
            else:
                db.execute('UPDATE projects SET name = ?, description = ? WHERE id = ?', 
                          (name, description, project_id))
        else:
            db.execute('UPDATE projects SET name = ?, description = ? WHERE id = ?', 
                      (name, description, project_id))
        
        db.commit()
        db.close()
    
    return redirect(url_for('project_detail', project_id=project_id))

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

@app.route('/task/<int:task_id>/update', methods=['POST'])
def update_task(task_id):
    """Update task or subtask name and description"""
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if name:
        db = get_db()
        task = db.execute('SELECT project_id FROM tasks WHERE id = ?', (task_id,)).fetchone()
        project_id = task['project_id'] if task else None
        
        db.execute('UPDATE tasks SET name = ?, description = ? WHERE id = ?', 
                  (name, description, task_id))
        db.commit()
        db.close()
        
        if project_id:
            return redirect(url_for('project_detail', project_id=project_id))
    
    return redirect(url_for('index'))

@app.route('/task/<int:task_id>/update-status', methods=['POST'])
def update_task_status(task_id):
    """Update task or subtask status"""
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

@app.route('/comment/<int:comment_id>')
def get_comment(comment_id):
    """Get a single comment's content"""
    db = get_db()
    comment = db.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    db.close()
    
    if comment:
        return jsonify({
            'id': comment['id'],
            'content': comment['content'],
            'author': comment['author'],
            'created_at': comment['created_at'],
            'entity_type': comment['entity_type'],
            'entity_id': comment['entity_id']
        })
    return jsonify({'error': 'Comment not found'}), 404

@app.route('/comment/<int:comment_id>/update', methods=['POST'])
def update_comment(comment_id):
    """Update a comment"""
    content = request.form.get('content')
    author = request.form.get('author')
    
    if content and author:
        db = get_db()
        db.execute('UPDATE comments SET content = ?, author = ? WHERE id = ?', 
                  (content, author, comment_id))
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    """Delete a comment"""
    db = get_db()
    comment = db.execute('SELECT entity_type, entity_id FROM comments WHERE id = ?', 
                        (comment_id,)).fetchone()
    
    if comment:
        db.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        db.commit()
        db.close()
        return jsonify({'success': True, 'entity_type': comment['entity_type'], 
                       'entity_id': comment['entity_id']})
    
    db.close()
    return jsonify({'success': False}), 404

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
