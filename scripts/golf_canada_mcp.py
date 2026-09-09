#!/usr/bin/env python3
import json
import os

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GolfCanada")

BASE_URL = "https://scg.golfcanada.ca"
TOKEN = os.getenv("GOLF_CANADA_TOKEN", "")


def _headers() -> dict:
    return {
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
    }


def _get_json(url: str) -> str:
    response = requests.get(url, headers=_headers(), timeout=10)
    response.raise_for_status()
    return json.dumps(response.json())


@mcp.tool()
def get_user_profile(individual_id: str) -> str:
    """Fetch profile information for a given Golf Canada individual ID."""
    try:
        return _get_json(f"{BASE_URL}/api/scores/getProfile?individualId={individual_id}")
    except Exception as exc:
        return f"Error fetching profile: {exc}"


@mcp.tool()
def get_user_round_history(individual_id: str, skip: int = 0, top: int = 20) -> str:
    """Fetch recent rounds for a given Golf Canada individual ID."""
    try:
        return _get_json(
            f"{BASE_URL}/api/scores/getHistory?$skip={skip}&$top={top}&individualId={individual_id}"
        )
    except Exception as exc:
        return f"Error fetching round history: {exc}"


@mcp.tool()
def get_user_round_details(score_id: str) -> str:
    """Fetch hole-by-hole details and metrics for a specific round/score ID."""
    try:
        return _get_json(f"{BASE_URL}/api/scores/getScoreDetails?scoreId={score_id}")
    except Exception as exc:
        return f"Error fetching round details: {exc}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
