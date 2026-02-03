"""Sample projects for demo mode."""
from typing import Dict, Optional


SAMPLE_PROJECTS = {
    "fastapi-todo": {
        "id": "fastapi-todo",
        "name": "FastAPI Todo API",
        "description": "A simple REST API for managing todo items built with FastAPI",
        "framework": "fastapi",
        "files": {
            "main.py": '''"""FastAPI Todo Application"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Todo API", version="1.0.0")

# In-memory storage
todos = []

class TodoItem(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    completed: bool = False

@app.get("/")
async def root():
    return {"message": "Welcome to Todo API"}

@app.get("/todos", response_model=List[TodoItem])
async def get_todos():
    return todos

@app.post("/todos", response_model=TodoItem)
async def create_todo(todo: TodoItem):
    todo.id = len(todos) + 1
    todos.append(todo)
    return todo

@app.get("/todos/{todo_id}", response_model=TodoItem)
async def get_todo(todo_id: int):
    for todo in todos:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}", response_model=TodoItem)
async def update_todo(todo_id: int, updated: TodoItem):
    for i, todo in enumerate(todos):
        if todo.id == todo_id:
            updated.id = todo_id
            todos[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    for i, todo in enumerate(todos):
        if todo.id == todo_id:
            todos.pop(i)
            return {"message": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")
''',
            "requirements.txt": '''fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
''',
            "README.md": '''# Todo API

A simple REST API for managing todo items.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
uvicorn main:app --reload
```

## Endpoints

- GET /todos - List all todos
- POST /todos - Create a new todo
- GET /todos/{id} - Get a specific todo
- PUT /todos/{id} - Update a todo
- DELETE /todos/{id} - Delete a todo

---
*This is a demo project from LaunchForge*
''',
        },
    },
    "flask-blog": {
        "id": "flask-blog",
        "name": "Flask Blog",
        "description": "A simple blog application built with Flask",
        "framework": "flask",
        "files": {
            "app.py": '''"""Flask Blog Application"""
from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# In-memory storage
posts = []

@app.route('/')
def home():
    return jsonify({"message": "Welcome to Flask Blog"})

@app.route('/posts', methods=['GET'])
def get_posts():
    return jsonify(posts)

@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json()
    post = {
        'id': len(posts) + 1,
        'title': data.get('title'),
        'content': data.get('content'),
        'author': data.get('author', 'Anonymous'),
        'created_at': datetime.now().isoformat()
    }
    posts.append(post)
    return jsonify(post), 201

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if post:
        return jsonify(post)
    return jsonify({"error": "Post not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
''',
            "requirements.txt": '''Flask==3.0.0
''',
            "README.md": '''# Flask Blog

A simple blog application.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

---
*This is a demo project from LaunchForge*
''',
        },
    },
}


def get_sample_project(project_id: Optional[str] = None) -> Optional[Dict]:
    """Get a sample project by ID, or return the default project.
    
    Args:
        project_id: Optional project ID to retrieve
        
    Returns:
        Sample project dictionary or None if not found
    """
    if project_id is None:
        # Return the first project as default
        if SAMPLE_PROJECTS:
            return list(SAMPLE_PROJECTS.values())[0]
        return None
    
    return SAMPLE_PROJECTS.get(project_id)


def list_sample_projects() -> Dict[str, Dict]:
    """List all available sample projects.
    
    Returns:
        Dictionary of sample projects
    """
    return SAMPLE_PROJECTS
