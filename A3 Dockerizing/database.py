import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    done = Column(Boolean, default=False, nullable=False)


_seed_tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Walk the dog", "done": True},
    {"id": 3, "title": "Read FastAPI docs", "done": False},
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Task).count() == 0:
            for task_data in _seed_tasks:
                db.add(Task(id=task_data["id"], title=task_data["title"], done=task_data["done"]))
            db.commit()
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
