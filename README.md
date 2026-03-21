# Fast Scrum Poker

A blazing fast, real-time Scrum Poker online clone built with FastAPI, WebSockets, and Vanilla JavaScript.

## Features
- Real-time voting via WebSockets
- Hide votes until the host reveals them
- Kick users, reset rounds
- Modern Glassmorphism dark-mode UI
- Backend tested with 97% `pytest` coverage

## Requirements
- Python 3.14+
- `uv` (Fast Python package and project manager)

## How to Start the App

1. **Install dependencies** (if you haven't already):
   ```bash
   uv sync
   ```

2. **Run the FastAPI server**:
   ```bash
   uv run uvicorn src.main:app --reload
   ```

3. **Open in browser**:
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Running Tests

To run the test suite and check coverage:
```bash
uv pip install -e .[dev]
uv run pytest --cov=src
```
