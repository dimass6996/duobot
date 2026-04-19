# DuoChat

Simple chat app: FastAPI backend + Flet desktop frontend.

## Commands

### Backend (run from project root)
```bash
python -m venv venv && source venv/bin/activate  # on first run
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
python frontend/main.py
```

### Docker
```bash
docker-compose up --build
```

## Architecture

- **Backend entrypoint**: `backend/main.py` - FastAPI app with WebSocket at `/ws/{user_id}`
- **DB**: SQLite at `backend/chat.db` (auto-created)
- **Uploads**: `uploads/` directory
- **API**: `/register`, `/login`, `/upload`
- **Frontend**: Flet desktop app, connects to `DUOCHAT_SERVER` env var (default: `localhost`)

## Important quirks

- Relative imports in backend (`from .models`), must run with `uvicorn backend.main:app` from project root
- Two `/upload` endpoints defined in backend (line 55 and 90) - the second one overrides (bug)
- Passwords stored as plaintext (noted in models.py:11)
- `page.update()` calls in frontend are synchronous (line 37, 57, 78, 115 - no `await`)