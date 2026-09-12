from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Task as DBTask, _seed_tasks, get_db, init_db
from auth import (
    supabase,
    get_current_user,
    UserSignUp,
    UserLogin,
)
from llm.schema import TriageRequest, TriageResponse
from llm.service import triage_message


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task, Auth & LLM Production API",
    version="1.0",
    description="A containerized CRUD, Supabase Auth, and Production LLM Triage API.",
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


# ==========================================
# Root & Health Endpoints
# ==========================================

@app.get("/", summary="API information")
def read_root():
    """Returns basic information about the API."""
    return {
        "name": "Task, Auth & LLM API",
        "version": "1.0",
        "endpoints": [
            "/tasks",
            "/auth/signup",
            "/auth/login",
            "/auth/logout",
            "/public/info",
            "/protected/profile",
            "/triage",
        ],
    }


@app.get("/health", summary="Health check")
def health_check():
    """Returns the health status of the server."""
    return {"status": "ok"}


# ==========================================
# Production LLM Triage Endpoint (W7)
# ==========================================

@app.post("/triage", response_model=TriageResponse, summary="LLM Support Triage", tags=["LLM Production"])
def triage_endpoint(payload: TriageRequest):
    """
    Classify support messages with structured JSON output schema enforcement,
    input validation, timeout protection, repair retry, quarantine logging, & kill switch.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text field is required and cannot be empty",
        )
    if len(payload.text) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text field exceeds maximum allowed limit of 2000 characters",
        )

    return triage_message(payload.text.strip())


# ==========================================
# Authentication & Authorization Endpoints (W4)
# ==========================================

@app.post("/auth/signup", status_code=status.HTTP_201_CREATED, summary="User Sign Up", tags=["Authentication"])
def signup(payload: UserSignUp):
    """Register a new user account with Supabase Auth."""
    if not payload.email or not payload.email.strip() or not payload.password or not payload.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email and password are required and cannot be empty",
        )

    try:
        res = supabase.auth.sign_up({
            "email": payload.email.strip(),
            "password": payload.password.strip(),
        })

        if not res or not res.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sign up failed",
            )

        user = res.user
        return {
            "message": "User registered successfully",
            "user": {
                "id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
                "created_at": getattr(user, "created_at", None),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign up error: {str(exc)}",
        )


@app.post("/auth/login", summary="User Log In", tags=["Authentication"])
def login(payload: UserLogin):
    """Authenticate user credentials and return JWT access token."""
    if not payload.email or not payload.email.strip() or not payload.password or not payload.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email and password are required and cannot be empty",
        )

    try:
        res = supabase.auth.sign_in_with_password({
            "email": payload.email.strip(),
            "password": payload.password.strip(),
        })

        if not res or not res.session or not res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials",
            )

        session = res.session
        user = res.user

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            },
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="User Log Out", tags=["Authentication"])
def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Sign out the current user session (Protected Endpoint)."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return None


@app.get("/public/info", summary="Public Open Information", tags=["Public Routes"])
def public_info():
    """Unprotected endpoint accessible to anyone."""
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", summary="Protected User Profile", tags=["Protected Routes"])
def protected_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Protected route accessible only with a valid Bearer token."""
    return {
        "message": "Protected profile retrieved successfully",
        "user": current_user,
    }


@app.get("/protected/dashboard", summary="Protected User Dashboard", tags=["Protected Routes"])
def protected_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Second protected route demonstrating reusable auth dependency."""
    return {
        "message": "Welcome to your protected dashboard!",
        "user_id": current_user["id"],
        "email": current_user["email"],
    }


# ==========================================
# Task CRUD Endpoints (Preserved from W2/W3)
# ==========================================

@app.get("/tasks", response_model=List[Task], summary="List tasks", tags=["Tasks"])
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


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task", tags=["Tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return a single task by its ID."""
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201, summary="Create a task", tags=["Tasks"])
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


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task", tags=["Tasks"])
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


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task", tags=["Tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task by its ID."""
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    db.delete(task)
    db.commit()
    return None


@app.get("/stats", summary="Task statistics", tags=["Tasks"])
def get_stats(db: Session = Depends(get_db)):
    """Return aggregate statistics about the task list computed via SQL."""
    total = db.query(func.count(DBTask.id)).scalar() or 0
    done = db.query(func.count(DBTask.id)).filter(DBTask.done == True).scalar() or 0
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset", response_model=List[Task], summary="Reset tasks", tags=["Tasks"])
def reset_tasks(db: Session = Depends(get_db)):
    """Reset the database task table back to the original seed tasks."""
    db.query(DBTask).delete()
    for task_data in _seed_tasks:
        db.add(DBTask(id=task_data["id"], title=task_data["title"], done=task_data["done"]))
    db.commit()
    return db.query(DBTask).order_by(DBTask.id).all()
