# Project Manager Application

A modern web-based project management application built with Flask, Bootstrap, and Docker. Manage your projects, tasks, subtasks, and collaborate with comments.

## Features

- **Project Management**: Create and manage multiple projects
- **Task Organization**: Add tasks to projects with status tracking (Pending, In Progress, Completed)
- **Subtask Support**: Break down tasks into smaller subtasks
- **Comments System**: Add comments to projects, tasks, and subtasks
- **Responsive Design**: Modern Bootstrap 5 UI that works on all devices
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **SQLite Database**: Lightweight, file-based database

## Project Structure

```
.
├── app.py                 # Main Flask application
├── templates/
│   ├── index.html        # Project list page
│   └── project_detail.html  # Project detail with tasks
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Requirements

### Option 1: Docker (Recommended)
- Docker
- Docker Compose

### Option 2: Local Installation
- Python 3.11 or higher
- pip

## Installation & Running

### Using Docker (Recommended)

1. **Build and start the container:**
   ```bash
   docker-compose up -d
   ```

2. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

3. **Stop the container:**
   ```bash
   docker-compose down
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

### Using Python (Local Development)

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

## Usage Guide

### Creating a Project

1. Click the **"New Project"** button on the home page
2. Enter project name and description
3. Click **"Create Project"**

### Managing Tasks

1. Click **"View Details"** on a project card
2. Click **"Add Task"** to create a new task
3. Use the task controls to:
   - Add subtasks (click the **"+"** button)
   - View subtasks and comments (click the **list** icon)
   - Change task status (click the **gear** icon)
   - Delete task (click the **trash** icon)

### Adding Comments

- **Project Comments**: Use the comment form in the right sidebar on the project detail page
- **Task Comments**: Expand a task's subtasks section to see and add comments

### Task Status

Tasks can have three statuses:
- **Pending** (Yellow) - Not started
- **In Progress** (Blue) - Currently being worked on
- **Completed** (Green) - Finished

## Database

The application uses SQLite with the following schema:

- **projects**: Stores project information
- **tasks**: Stores tasks and subtasks (self-referencing for subtasks)
- **comments**: Stores comments for projects and tasks

The database file is stored in:
- Docker: `./data/projects.db`
- Local: `./projects.db`

## Development

### File Structure

- `app.py`: Main application logic, routes, and database operations
- `templates/index.html`: Home page with project list
- `templates/project_detail.html`: Project details with tasks and comments
- `Dockerfile`: Container configuration
- `docker-compose.yml`: Multi-container orchestration
- `requirements.txt`: Python package dependencies

### Customization

You can customize the application by:

1. **Changing the port**: Edit `docker-compose.yml` or use environment variable
2. **Styling**: Modify Bootstrap classes in templates
3. **Adding features**: Extend the Flask routes in `app.py`
4. **Database location**: Change `DATABASE` config in `app.py`

## Technical Stack

- **Backend**: Flask 3.0
- **Frontend**: Bootstrap 5.3, Bootstrap Icons
- **Database**: SQLite 3
- **Containerization**: Docker, Docker Compose
- **Python**: 3.11

## API Endpoints

- `GET /` - List all projects
- `POST /project/add` - Create a new project
- `GET /project/<id>` - View project details
- `POST /project/<id>/delete` - Delete a project
- `POST /task/add` - Create a new task/subtask
- `GET /task/<id>/subtasks` - Get subtasks and comments (JSON)
- `POST /task/<id>/update-status` - Update task status
- `POST /task/<id>/delete` - Delete a task
- `POST /comment/add` - Add a comment

## Troubleshooting

### Database Locked Error
If you see a "database is locked" error, ensure only one instance is running.

### Port Already in Use
If port 5000 is already in use, change it in `docker-compose.yml`:
```yaml
ports:
  - "8000:5000"  # Use port 8000 instead
```

### Container Won't Start
Check logs with:
```bash
docker-compose logs web
```

## License

This project is open source and available for modification and distribution.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
