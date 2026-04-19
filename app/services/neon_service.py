"""Neon Console API client for managing branches (= database snapshot backups).

Only for use by superadmin endpoints. All calls go server-side; API key must
never be exposed to the frontend.
"""

import logging
import os
from typing import Optional

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

NEON_API_BASE = "https://console.neon.tech/api/v2"


def _config() -> tuple[str, str]:
    """Read env vars at call time so tests can patch them via monkeypatch."""
    api_key = os.getenv("NEON_API_KEY")
    project_id = os.getenv("NEON_PROJECT_ID")
    if not api_key or not project_id:
        raise HTTPException(
            status_code=500,
            detail="Neon API not configured. Set NEON_API_KEY and NEON_PROJECT_ID.",
        )
    return api_key, project_id


def _headers(api_key: str, include_json: bool = False) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


async def list_branches() -> list[dict]:
    """Return all branches in the project."""
    api_key, project_id = _config()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{NEON_API_BASE}/projects/{project_id}/branches",
            headers=_headers(api_key),
        )
    if resp.status_code != 200:
        logger.error("Neon list_branches failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail=f"Neon API error: {resp.status_code}")
    return resp.json().get("branches", [])


async def get_default_branch_id() -> str:
    """Return the ID of the default (production) branch."""
    for b in await list_branches():
        if b.get("default") is True:
            return b["id"]
    raise HTTPException(status_code=500, detail="No default branch found")


async def create_branch(name: str, parent_branch_id: Optional[str] = None) -> dict:
    """Create a new branch from the given parent (or the default branch)."""
    api_key, project_id = _config()
    if not parent_branch_id:
        parent_branch_id = await get_default_branch_id()

    # No "endpoints" key → compute stays stopped, minimising cost.
    payload = {"branch": {"name": name, "parent_id": parent_branch_id}}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NEON_API_BASE}/projects/{project_id}/branches",
            headers=_headers(api_key, include_json=True),
            json=payload,
        )

    if resp.status_code not in (200, 201):
        logger.error("Neon create_branch failed: %s %s", resp.status_code, resp.text)
        # Surface client errors (e.g. duplicate name, invalid chars) verbatim.
        if 400 <= resp.status_code < 500:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Neon API error: {resp.text}",
            )
        raise HTTPException(status_code=502, detail=f"Neon API error: {resp.status_code}")

    return resp.json()


async def delete_branch(branch_id: str) -> None:
    """Delete a branch. Neon rejects the call if the branch is default or has children."""
    api_key, project_id = _config()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{NEON_API_BASE}/projects/{project_id}/branches/{branch_id}",
            headers=_headers(api_key),
        )
    if resp.status_code not in (200, 202):
        logger.error("Neon delete_branch failed: %s %s", resp.status_code, resp.text)
        if 400 <= resp.status_code < 500:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Neon API error: {resp.text}",
            )
        raise HTTPException(status_code=502, detail=f"Neon API error: {resp.status_code}")
