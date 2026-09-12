# Task API (SQLite Database-Backed)

A CRUD REST API for managing a to-do list, built with Python, FastAPI, and SQLite (via SQLAlchemy) as part of the FlyRank Backend Track internship (Week 3, Assignment A2).

Moving from Assignment 1's in-memory storage, this API persists all tasks to a real SQLite database (`tasks.db`), ensuring data survives server restarts while preserving identical API contracts and status codes.

---

## Contents

- [Why SQLite?](#why-sqlite)
- [Database Schema & Automatic Initialization](#database-schema--automatic-initialization)
- [Run it](#run-it)
- [Endpoints](#endpoints)
- [Example SQL Queries](#example-sql-queries)
- [Example curl Session](#example-curl-session)
- [Swagger UI](#swagger-ui)
- [Proof of Persistence](#proof-of-persistence)
- [Optional Extras Included](#optional-extras-included)

---

## Why SQLite?

1. **Serverless & Zero-Config:** SQLite requires no standalone database server setup or process management. It operates directly against a single local file (`tasks.db`).
2. **Persistence:** Unlike in-memory lists, data stored in SQLite is written to disk, surviving server restarts and application crashes.
3. **Lightweight & Fast:** Ideal for local development, rapid prototyping, and embedded applications with zero setup overhead.

---

## Database Schema & Automatic Initialization

The database table `tasks` is auto-created on application startup if it does not exist:

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique task identifier |
| `title` | TEXT | NOT NULL | Task description / title |
| `done` | BOOLEAN | NOT NULL (Default: `0`) | Completion status |

### Automatic Seeding

When the server starts up, it checks if the `tasks` table is empty. If empty (`count == 0`), it automatically seeds the 3 default tasks:
1. `{"id": 1, "title": "Buy milk", "done": false}`
2. `{"id": 2, "title": "Walk the dog", "done": true}`
3. `{"id": 3, "title": "Read FastAPI docs", "done": false}`

Subsequent server restarts detect existing data and do not duplicate seed rows.

---

## Run it

Make sure you are in the project folder and using the virtual environment:

```bash
cd "CRUD API"
..\.venv\Scripts\uvicorn main:app --reload
```

Then open your browser:

- API root: `http://localhost:8000/`
- Health check: `http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`

---

## Endpoints

| Method | Path | Description | Status Codes |
|---|---|---|---|
| GET | `/` | API information | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List tasks (supports `?done=`, `?search=`, `?limit=`, `?offset=`) | 200 |
| GET | `/tasks/{id}` | Get single task by ID | 200, 404 |
| POST | `/tasks` | Create a new task (database assigns ID, sets `done=false`) | 201, 400 |
| PUT | `/tasks/{id}` | Update task title and/or `done` status | 200, 400, 404 |
| DELETE | `/tasks/{id}` | Delete a task | 204, 404 |
| GET | `/stats` | Aggregate task statistics computed in SQL (`total`, `done`, `open`) | 200 |
| POST | `/reset` | Truncate and re-seed database with 3 initial tasks | 200 |

---

## Example SQL Queries

These SQL queries demonstrate direct interaction with `tasks.db` (via DB Browser for SQLite or SQL client):

```sql
-- 1. List all tasks
SELECT * FROM tasks;

-- 2. Query completed tasks
SELECT * FROM tasks WHERE done = 1;

-- 3. Count total tasks
SELECT COUNT(*) FROM tasks;

-- 4. Mark a task as completed
UPDATE tasks SET done = 1 WHERE id = 1;

-- 5. Delete a completed task
DELETE FROM tasks WHERE done = 1;
```

---

## Example curl Session

### Read all tasks

```bash
curl -i http://localhost:8000/tasks
```

Output:
```http
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"title":"Buy milk","done":false},{"id":2,"title":"Walk the dog","done":true},{"id":3,"title":"Read FastAPI docs","done":false}]
```

### Full CRUD Cycle

1. **Create** a task:
   ```bash
   curl -i -X POST http://localhost:8000/tasks \
     -H "Content-Type: application/json" \
     -d "{\"title\":\"Build SQLite database API\"}"
   ```

2. **Read** single task:
   ```bash
   curl -i http://localhost:8000/tasks/4
   ```

3. **Update** task completion status:
   ```bash
   curl -i -X PUT http://localhost:8000/tasks/4 \
     -H "Content-Type: application/json" \
     -d "{\"done\":true}"
   ```

4. **Delete** task:
   ```bash
   curl -i -X DELETE http://localhost:8000/tasks/4
   ```

---

## DB Browser Screenshot

Here is the database file (`tasks.db`) opened in DB Browser for SQLite showing the `tasks` table and its seeded records:

![DB Browser Screenshot](database_image.png)

---

## Swagger UI

FastAPI automatically generates interactive OpenAPI documentation at `/docs`. You can inspect endpoints, view schemas, and execute live queries directly in the browser.

---

## Proof of Persistence

Unlike Week 2 where tasks vanished on server restart:
1. Create a task via `POST /tasks`.
2. Stop the uvicorn server (`Ctrl+C`).
3. Start the server again (`uvicorn main:app --reload`).
4. Perform `GET /tasks` — your created task remains present in `tasks.db`!
