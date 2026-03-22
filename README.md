# Fast Scrum Poker

A blazing fast, real-time Scrum Poker online clone built with FastAPI, WebSockets, and Vanilla JavaScript.

## Features
- Real-time voting via WebSockets
- Hide votes until the host reveals them
- Modern Glassmorphism dark-mode UI

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

## Optional Jira Integration

Fast Scrum Poker includes an optional Jira integration that allows the room host to fetch issue details (summary and description) and push estimated story points directly back to Jira without leaving the room.

To enable this feature, provide the following environment variables when running the application:

- `JIRA_URL`: Your Jira instance URL (e.g., `https://yourdomain.atlassian.net`)
- `JIRA_TOKEN`: Your Jira API Token or Personal Access Token (PAT)
- `JIRA_EMAIL` *(Optional)*: The email address associated with your API token (required for Jira Cloud Basic Auth).
- `JIRA_STORY_POINTS_FIELD` *(Optional)*: The custom field ID for Story Points in your Jira instance. Defaults to `customfield_10016`.

**Usage:**
1. When enabled, the room host will see a **Jira Integration** panel beneath the host controls.
2. Enter a Jira Issue Key (e.g., `PROJ-123`) and click **Fetch Issue**. The issue summary and description will immediately appear at the top of the table for all participants.
3. After the team votes and the cards are revealed, the host can enter the final agreed-upon points and click **Save Points** to automatically push them to the Jira ticket.
