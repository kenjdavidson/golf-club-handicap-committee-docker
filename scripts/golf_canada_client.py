#!/usr/bin/env python3
"""Golf Canada API client with username/password authentication and token refresh."""
import json
import os
from dataclasses import dataclass, field
from typing import Optional

import requests

BASE_URL = "https://scg.golfcanada.ca"
TOKEN_URL = f"{BASE_URL}/connect/token"
TOKEN_SCOPE = "address email offline_access openid phone profile roles"


@dataclass
class GolfCanadaToken:
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    user: dict = field(default_factory=dict)


class GolfCanadaAuthError(Exception):
    """Raised when authentication fails."""


class GolfCanadaClient:
    """Client for the Golf Canada SCG API.

    Authentication can be supplied in two ways:
    1. Provide a pre-existing ``token`` string (******
    2. Call :meth:`login` with a username and password to obtain a token.

    The token can be refreshed via :meth:`refresh` when a ``refresh_token``
    is available.
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self._token: Optional[str] = token
        self._refresh_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> GolfCanadaToken:
        """Authenticate with username and password.

        Stores the resulting access and refresh tokens internally so that
        subsequent API calls use them automatically.

        Returns the :class:`GolfCanadaToken` on success; raises
        :class:`GolfCanadaAuthError` on failure.
        """
        try:
            response = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "scope": TOKEN_SCOPE,
                },
                timeout=15,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise GolfCanadaAuthError(f"Login failed: {exc}") from exc
        except requests.RequestException as exc:
            raise GolfCanadaAuthError(f"Login request error: {exc}") from exc

        data = response.json()
        token = GolfCanadaToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
            user=data.get("user", {}),
        )
        self._token = token.access_token
        self._refresh_token = token.refresh_token
        return token

    def refresh(self, password: str) -> GolfCanadaToken:
        """Refresh the current access token using the stored refresh token.

        ``password`` is required by the Golf Canada token endpoint even for
        refresh_token grants.

        Returns the updated :class:`GolfCanadaToken`; raises
        :class:`GolfCanadaAuthError` if no refresh token is stored or the
        request fails.
        """
        if not self._refresh_token:
            raise GolfCanadaAuthError("No refresh token available; call login() first.")

        try:
            response = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "password": password,
                    "scope": TOKEN_SCOPE,
                },
                timeout=15,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise GolfCanadaAuthError(f"Token refresh failed: {exc}") from exc
        except requests.RequestException as exc:
            raise GolfCanadaAuthError(f"Refresh request error: {exc}") from exc

        data = response.json()
        token = GolfCanadaToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", self._refresh_token),
            expires_in=data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
            user=data.get("user", {}),
        )
        self._token = token.access_token
        self._refresh_token = token.refresh_token
        return token

    def set_token(self, token: str) -> None:
        """Set a pre-existing ****** directly."""
        self._token = token

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        if not self._token:
            raise GolfCanadaAuthError(
                "No token available. Call login() or set_token() first."
            )
        return {
            "Authorization": f"******",
            "Content-Type": "application/json",
        }

    def _get_json(self, url: str) -> str:
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        return json.dumps(response.json())

    # ------------------------------------------------------------------
    # API methods
    # ------------------------------------------------------------------

    def get_user_profile(self, individual_id: str) -> str:
        """Fetch profile information for a given Golf Canada individual ID."""
        return self._get_json(
            f"{BASE_URL}/api/scores/getProfile?individualId={individual_id}"
        )

    def get_user_round_history(
        self, individual_id: str, skip: int = 0, top: int = 20
    ) -> str:
        """Fetch recent rounds for a given Golf Canada individual ID."""
        return self._get_json(
            f"{BASE_URL}/api/scores/getHistory?$skip={skip}&$top={top}&individualId={individual_id}"
        )

    def get_user_round_details(self, score_id: str) -> str:
        """Fetch hole-by-hole details and metrics for a specific round/score ID."""
        return self._get_json(
            f"{BASE_URL}/api/scores/getScoreDetails?scoreId={score_id}"
        )


def client_from_env() -> GolfCanadaClient:
    """Create a :class:`GolfCanadaClient` from environment variables.

    Looks for ``GOLF_CANADA_TOKEN`` first; if absent, falls back to
    ``GOLFCANADA_USERNAME`` / ``GOLFCANADA_PASSWORD`` and calls
    :meth:`GolfCanadaClient.login` automatically.
    """
    token = os.getenv("GOLF_CANADA_TOKEN", "")
    if token:
        return GolfCanadaClient(token=token)

    username = os.getenv("GOLFCANADA_USERNAME", "")
    password = os.getenv("GOLFCANADA_PASSWORD", "")
    if username and password:
        client = GolfCanadaClient()
        client.login(username, password)
        return client

    return GolfCanadaClient()
