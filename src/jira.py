import os
import httpx
import logging

logger = logging.getLogger(__name__)

# Config
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
JIRA_STORY_POINTS_FIELD = os.environ.get("JIRA_STORY_POINTS_FIELD", "customfield_10016")

IS_ENABLED = bool(JIRA_URL and JIRA_TOKEN)

def get_auth():
    if JIRA_EMAIL:
        return (JIRA_EMAIL, JIRA_TOKEN)
    return None

def get_headers():
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if not JIRA_EMAIL and JIRA_TOKEN:
        headers["Authorization"] = f"Bearer {JIRA_TOKEN}"
    return headers

async def get_issue(issue_key: str) -> dict | None:
    if not IS_ENABLED:
        return None

    url = f"{JIRA_URL.rstrip('/')}/rest/api/2/issue/{issue_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            auth = get_auth()
            kwargs = {"headers": get_headers()}
            if auth:
                kwargs["auth"] = auth
                
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            
            data = response.json()
            fields = data.get("fields", {})
            return {
                "key": issue_key,
                "summary": fields.get("summary", ""),
                "description": fields.get("description", "")
            }
    except Exception as e:
        logger.error(f"Failed to fetch Jira issue {issue_key}: {e}")
        return None

async def update_story_points(issue_key: str, points: float) -> bool:
    if not IS_ENABLED:
        return False

    url = f"{JIRA_URL.rstrip('/')}/rest/api/2/issue/{issue_key}"
    
    payload = {
        "fields": {
            JIRA_STORY_POINTS_FIELD: points
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            auth = get_auth()
            kwargs = {"headers": get_headers(), "json": payload}
            if auth:
                kwargs["auth"] = auth
                
            response = await client.put(url, **kwargs)
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Failed to update Jira issue {issue_key} with points {points}: {e}")
        return False
