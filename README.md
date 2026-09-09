# Task API

A small in-memory CRUD API for managing a to-do list, built with Python and FastAPI as part of the FlyRank Backend Track internship (Week 2, Assignment A1).

The API supports creating, reading, updating, and deleting tasks. Data lives only in memory, so it resets to the seed tasks whenever the server restarts.

## Run it

Make sure you are in the project folder and using the virtual environment at the repository root:

```bash
cd "CRUD API"
..\.venv\Scripts\uvicorn main:app --reload
```

Then open your browser:

- API root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

> **Note:** If port `8000` is unavailable on your machine, pick another port, e.g. `..\.venv\Scripts\uvicorn main:app --port 8765`.

## Endpoints

| Method | Path | Description | Status codes |
|--------|------|-------------|--------------|
| GET | `/` | API information | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks (supports `?done=`, `?search=`, `?limit=`, `?offset=`) | 200 |
| GET | `/tasks/{id}` | Get a single task | 200, 404 |
| POST | `/tasks` | Create a new task | 201, 400 |
| PUT | `/tasks/{id}` | Update a task's title and/or `done` status | 200, 400, 404 |
| DELETE | `/tasks/{id}` | Delete a task | 204, 404 |
| GET | `/stats` | Task statistics (`total`, `done`, `open`) | 200 |
| POST | `/reset` | Reset tasks to the original 3 seed tasks | 200 |

## Example curl session

```bash
curl -i http://localhost:8000/tasks/1
```

Output:

```http
HTTP/1.1 200 OK
content-type: application/json

{"id":1,"title":"Buy milk","done":false}
```

Full CRUD cycle:

```bash
# Create
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{\"title\":\"Buy milk\"}"

# Read all
curl -i http://localhost:8000/tasks

# Update (use the id returned by POST)
curl -i -X PUT http://localhost:8000/tasks/4 -H "Content-Type: application/json" -d "{\"done\":true}"

# Delete
curl -i -X DELETE http://localhost:8000/tasks/4
```

## Swagger UI

FastAPI generates interactive documentation automatically. Visit `/docs` to see every endpoint and try them out without curl.

![Swagger UI screenshot](docs/swagger-screenshot.png)

> Add your own screenshot of `http://localhost:8000/docs` at `docs/swagger-screenshot.png`.

## The mortality experiment

Create a few tasks, restart the server, then call `GET /tasks` again. The new tasks are gone and only the original 3 seed tasks remain. This happens because the "database" is just a Python list in memory; when the process stops, the list disappears. Next week we fix this with a real database.

## Optional extras included

- **Filtering:** `GET /tasks?done=true`
- **Search:** `GET /tasks?search=milk`
- **Pagination:** `GET /tasks?limit=2&offset=2`
- **Stats:** `GET /stats`
- **Reset:** `POST /reset`
