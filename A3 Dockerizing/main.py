from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Task as DBTask, _seed_tasks, get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A SQLite database-backed CRUD API for managing a to-do list.",
    lifespan=lifespan,
)


class Task(BaseModel):
    id: int
    title: str
    done: bool

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the task")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New title for the task")
    done: Optional[bool] = Field(None, description="New done status for the task")


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
    db: Session = Depends(get_db),
):
    """List all tasks. Supports filtering, searching, and pagination."""
    query = db.query(DBTask)

    if done is not None:
        query = query.filter(DBTask.done == done)

    if search:
        query = query.filter(DBTask.title.ilike(f"%{search}%"))

    query = query.order_by(DBTask.id)
    query = query.offset(offset)

    if limit is not None:
        query = query.limit(limit)

    return query.all()


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return a single task by its ID."""
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201, summary="Create a task")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task. The database assigns the ID and sets done to false."""
    if payload.title is None or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")

    new_task = DBTask(
        title=payload.title.strip(),
        done=False,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task's title and/or done status."""
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if payload.title is None and payload.done is None:
        raise HTTPException(status_code=400, detail="Request body must contain title or done")

    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(status_code=400, detail="title cannot be empty")
        task.title = payload.title.strip()
    if payload.done is not None:
        task.done = payload.done

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task by its ID."""
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    db.delete(task)
    db.commit()
    return None


@app.get("/stats", summary="Task statistics")
def get_stats(db: Session = Depends(get_db)):
    """Return aggregate statistics about the task list computed via SQL."""
    total = db.query(func.count(DBTask.id)).scalar() or 0
    done = db.query(func.count(DBTask.id)).filter(DBTask.done == True).scalar() or 0
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset", response_model=List[Task], summary="Reset tasks")
def reset_tasks(db: Session = Depends(get_db)):
    """Reset the database task table back to the original seed tasks."""
    db.query(DBTask).delete()
    for task_data in _seed_tasks:
        db.add(DBTask(id=task_data["id"], title=task_data["title"], done=task_data["done"]))
    db.commit()
    return db.query(DBTask).order_by(DBTask.id).all()
