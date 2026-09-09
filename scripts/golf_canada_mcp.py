#!/usr/bin/env python3
import sys
import os

# Allow importing golf_canada_client from the same directory
sys.path.insert(0, os.path.dirname(__file__))

from golf_canada_client import client_from_env  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("GolfCanada")

_client = client_from_env()


@mcp.tool()
def get_user_profile(individual_id: str) -> str:
    """Fetch profile information for a given Golf Canada individual ID."""
    try:
        return _client.get_user_profile(individual_id)
    except Exception as exc:
        return f"Error fetching profile: {exc}"


@mcp.tool()
def get_user_round_history(individual_id: str, skip: int = 0, top: int = 20) -> str:
    """Fetch recent rounds for a given Golf Canada individual ID."""
    try:
        return _client.get_user_round_history(individual_id, skip=skip, top=top)
    except Exception as exc:
        return f"Error fetching round history: {exc}"


@mcp.tool()
def get_user_round_details(score_id: str) -> str:
    """Fetch hole-by-hole details and metrics for a specific round/score ID."""
    try:
        return _client.get_user_round_details(score_id)
    except Exception as exc:
        return f"Error fetching round details: {exc}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
