# Task & Auth API (Full-Stack Containerized & Authenticated API)

A production-grade REST API managing tasks with database persistence (SQLite/PostgreSQL) and user authentication (Supabase Auth & JWT Bearer verification), built as part of the FlyRank Backend Track internship (Week 2-4, Assignments A1-A4).

---

## Features

- **User Authentication:** Sign up, Log in, Log out via Supabase Auth.
- **JWT Protection:** Protected routes verified using `Authorization: Bearer <token>` middleware.
- **Interactive Swagger UI:** `/docs` with built-in **Authorize** padlock button for testing bearer tokens.
- **Dual Database Support:** Instant local execution with **SQLite** (`tasks.db`) and full containerization with **PostgreSQL** in Docker.
- **Task CRUD Operations:** Full task management with parameterized queries, search, status filtering, and pagination.

---

## Contents

- [Environment Setup](#environment-setup)
- [Auth & API Endpoints Table](#auth--api-endpoints-table)
- [Authentication Flow](#authentication-flow)
- [Run with Docker Compose](#run-with-docker-compose)
- [Run Locally (SQLite)](#run-locally-sqlite)
- [Example curl Session](#example-curl-session)
- [Swagger UI Bearer Auth](#swagger-ui-bearer-auth)
- [DB Browser Screenshot](#db-browser-screenshot)

---

## Environment Setup

Copy `.env.example` to `.env` and fill in your secrets:

```bash
cp .env.example .env
```

```env
# Database configuration
DATABASE_URL=sqlite:///./tasks.db

# Supabase Auth configuration (From Supabase Dashboard -> Project Settings -> API)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

> **Note:** `.env` is listed in `.gitignore` and must never be committed.

---

## Auth & API Endpoints Table

| Method | Path | Description | Auth Required | Status Codes |
|---|---|---|---|---|
| POST | `/auth/signup` | Register a new user account | No | 201, 400 |
| POST | `/auth/login` | Authenticate user and return JWT | No | 200, 400, 401 |
| POST | `/auth/logout` | End current user session | Yes (`Bearer`) | 204, 401 |
| GET | `/public/info` | Open public information | No | 200 |
| GET | `/protected/profile` | Read authenticated user profile | Yes (`Bearer`) | 200, 401 |
| GET | `/protected/dashboard` | Read authenticated user dashboard | Yes (`Bearer`) | 200, 401 |
| GET | `/` | API metadata | No | 200 |
| GET | `/health` | Health check | No | 200 |
| GET | `/tasks` | List tasks (supports filtering & search) | No | 200 |
| GET | `/tasks/{id}` | Get single task | No | 200, 404 |
| POST | `/tasks` | Create a new task | No | 201, 400 |
| PUT | `/tasks/{id}` | Update task title and status | No | 200, 400, 404 |
| DELETE | `/tasks/{id}` | Delete task | No | 204, 404 |
| GET | `/stats` | Aggregate task statistics | No | 200 |
| POST | `/reset` | Re-seed initial tasks | No | 200 |

---

## Authentication Flow

1. **Sign Up (`POST /auth/signup`)**: Pass `{"email": "user@example.com", "password": "password123"}`.
2. **Log In (`POST /auth/login`)**: Pass `{"email": "user@example.com", "password": "password123"}` to receive `access_token` (JWT).
3. **Call Protected Endpoint**: Attach header `Authorization: Bearer <access_token>` to request `/protected/profile`.
4. **Log Out (`POST /auth/logout`)**: Call logout with Bearer token to sign out session.

---

## Run with Docker Compose

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

---

## Run Locally (SQLite)

```bash
cd "CRUD API"
..\.venv\Scripts\uvicorn main:app --reload
```

---

## Example curl Session

### 1. Sign Up
```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"secret123\"}"
```

### 2. Log In
```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"secret123\"}"
```

### 3. Call Protected Profile Endpoint
```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

### 4. Unauthenticated Call (Returns 401)
```bash
curl -i http://localhost:8000/protected/profile
# Output: HTTP/1.1 401 Unauthorized -> {"detail": "Access token required"}
```

---

## Swagger UI Bearer Auth

FastAPI configures `HTTPBearer` automatically.
1. Open `http://localhost:8000/docs`.
2. Click the green **Authorize** button at the top right.
3. Paste your JWT access token and click **Authorize**.
4. Test `/protected/profile` directly from the browser!

---

## DB Browser Screenshot

![DB Browser Screenshot](database_image.png)
