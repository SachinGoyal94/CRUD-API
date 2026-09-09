from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small in-memory CRUD API for managing a to-do list.",
)


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the task")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New title for the task")
    done: Optional[bool] = Field(None, description="New done status for the task")


# In-memory "database" — data is lost when the server restarts.
_seed_tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Walk the dog", "done": True},
    {"id": 3, "title": "Read FastAPI docs", "done": False},
]

tasks: List[dict] = [task.copy() for task in _seed_tasks]
_next_id = max(task["id"] for task in tasks) + 1 if tasks else 1


def _task_or_404(task_id: int) -> dict:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.get("/", summary="API information")
def read_root():
    """Returns basic information about the API."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Health check")
def health_check():
    """Returns the health status of the server."""
    return {"status": "ok"}


@app.get("/tasks", response_model=List[Task], summary="List tasks")
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search in task titles"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
):
    """List all tasks. Supports filtering, searching, and pagination."""
    result = tasks[:]

    if done is not None:
        result = [task for task in result if task["done"] == done]

    if search:
        result = [task for task in result if search.lower() in task["title"].lower()]

    total_after_filters = len(result)
    result = result[offset:]
    if limit is not None:
        result = result[:limit]

    return result


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int):
    """Return a single task by its ID."""
    return _task_or_404(task_id)


@app.post("/tasks", response_model=Task, status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    """Create a new task. The server assigns the ID and sets done to false."""
    if payload.title is None or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")

    global _next_id
    new_task = {
        "id": _next_id,
        "title": payload.title.strip(),
        "done": False,
    }
    _next_id += 1
    tasks.append(new_task)
    return new_task


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    """Update a task's title and/or done status."""
    task = _task_or_404(task_id)

    if payload.title is None and payload.done is None:
        raise HTTPException(status_code=400, detail="Request body must contain title or done")

    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(status_code=400, detail="title cannot be empty")
        task["title"] = payload.title.strip()
    if payload.done is not None:
        task["done"] = payload.done

    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Delete a task by its ID."""
    task = _task_or_404(task_id)
    tasks.remove(task)
    return None


@app.get("/stats", summary="Task statistics")
def get_stats():
    """Return aggregate statistics about the task list."""
    total = len(tasks)
    done = sum(1 for task in tasks if task["done"])
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset", summary="Reset tasks")
def reset_tasks():
    """Reset the in-memory task list back to the original seed tasks."""
    global tasks, _next_id
    tasks = [task.copy() for task in _seed_tasks]
    _next_id = max(task["id"] for task in tasks) + 1 if tasks else 1
    return tasks
