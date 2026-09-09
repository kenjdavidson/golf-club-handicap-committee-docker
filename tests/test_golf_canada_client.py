"""Tests for golf_canada_client.py.

Unit tests use mocked HTTP responses and do not require network access.

Integration tests (marked ``integration``) read credentials from the
environment variables ``GOLFCANADA_USERNAME`` and ``GOLFCANADA_PASSWORD``
and make real requests to the Golf Canada API.  They are skipped
automatically when those variables are not set.
"""
import json
import os
import sys

import pytest
import requests
from unittest.mock import MagicMock, patch

# Allow importing from the scripts directory without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from golf_canada_client import (  # noqa: E402
    BASE_URL,
    TOKEN_URL,
    GolfCanadaAuthError,
    GolfCanadaClient,
    GolfCanadaToken,
    client_from_env,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

FAKE_TOKEN_RESPONSE = {
    "token_type": "Bearer",
    "access_token": "fake_access_token",
    "expires_in": 3600,
    "refresh_token": "fake_refresh_token",
    "id_token": "fake_id_token",
    "user": {
        "id": 1,
        "username": "TESTUSER",
        "fullName": "Test User",
        "handicap": "10.0",
    },
}


def _mock_post_ok(url, data=None, **kwargs):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = FAKE_TOKEN_RESPONSE
    resp.raise_for_status = MagicMock()
    return resp


def _mock_post_fail(url, data=None, **kwargs):
    resp = MagicMock()
    resp.status_code = 401
    http_err = requests.HTTPError("401 Unauthorized", response=resp)
    resp.raise_for_status.side_effect = http_err
    return resp


def _mock_get_ok(url, headers=None, **kwargs):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": "ok"}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Unit tests — GolfCanadaClient.login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_login_success_returns_token(self):
        with patch("requests.post", side_effect=_mock_post_ok):
            client = GolfCanadaClient()
            token = client.login("user", "pass")

        assert isinstance(token, GolfCanadaToken)
        assert token.access_token == "fake_access_token"
        assert token.refresh_token == "fake_refresh_token"
        assert token.user["username"] == "TESTUSER"

    def test_login_stores_access_token_internally(self):
        with patch("requests.post", side_effect=_mock_post_ok):
            client = GolfCanadaClient()
            client.login("user", "pass")

        assert client._token == "fake_access_token"

    def test_login_stores_refresh_token_internally(self):
        with patch("requests.post", side_effect=_mock_post_ok):
            client = GolfCanadaClient()
            client.login("user", "pass")

        assert client._refresh_token == "fake_refresh_token"

    def test_login_failure_raises_auth_error(self):
        with patch("requests.post", side_effect=_mock_post_fail):
            client = GolfCanadaClient()
            with pytest.raises(GolfCanadaAuthError):
                client.login("bad", "creds")

    def test_login_network_error_raises_auth_error(self):
        with patch("requests.post", side_effect=requests.ConnectionError("network down")):
            client = GolfCanadaClient()
            with pytest.raises(GolfCanadaAuthError):
                client.login("user", "pass")

    def test_login_posts_to_token_url(self):
        with patch("requests.post", side_effect=_mock_post_ok) as mock_post:
            client = GolfCanadaClient()
            client.login("myuser", "mypass")

        call_args = mock_post.call_args
        assert call_args[0][0] == TOKEN_URL
        assert call_args[1]["data"]["grant_type"] == "password"
        assert call_args[1]["data"]["username"] == "myuser"
        assert call_args[1]["data"]["password"] == "mypass"


# ---------------------------------------------------------------------------
# Unit tests — GolfCanadaClient.refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_refresh_success_returns_token(self):
        with patch("requests.post", side_effect=_mock_post_ok):
            client = GolfCanadaClient()
            client._refresh_token = "old_refresh"
            token = client.refresh("pass")

        assert token.access_token == "fake_access_token"

    def test_refresh_without_stored_token_raises(self):
        client = GolfCanadaClient()
        with pytest.raises(GolfCanadaAuthError):
            client.refresh("pass")

    def test_refresh_posts_grant_type_refresh_token(self):
        with patch("requests.post", side_effect=_mock_post_ok) as mock_post:
            client = GolfCanadaClient()
            client._refresh_token = "old_refresh"
            client.refresh("mypass")

        call_args = mock_post.call_args
        assert call_args[1]["data"]["grant_type"] == "refresh_token"
        assert call_args[1]["data"]["refresh_token"] == "old_refresh"
        assert call_args[1]["data"]["password"] == "mypass"

    def test_refresh_failure_raises_auth_error(self):
        with patch("requests.post", side_effect=_mock_post_fail):
            client = GolfCanadaClient()
            client._refresh_token = "old_refresh"
            with pytest.raises(GolfCanadaAuthError):
                client.refresh("pass")


# ---------------------------------------------------------------------------
# Unit tests — GolfCanadaClient API methods
# ---------------------------------------------------------------------------


class TestApiMethods:
    def _authed_client(self):
        client = GolfCanadaClient(token="tok")
        return client

    def test_get_user_profile_calls_correct_url(self):
        with patch("requests.get", side_effect=_mock_get_ok) as mock_get:
            self._authed_client().get_user_profile("123")

        url = mock_get.call_args[0][0]
        assert "/api/scores/getProfile" in url
        assert "individualId=123" in url

    def test_get_user_round_history_calls_correct_url(self):
        with patch("requests.get", side_effect=_mock_get_ok) as mock_get:
            self._authed_client().get_user_round_history("456", skip=0, top=10)

        url = mock_get.call_args[0][0]
        assert "/api/scores/getHistory" in url
        assert "individualId=456" in url

    def test_get_user_round_details_calls_correct_url(self):
        with patch("requests.get", side_effect=_mock_get_ok) as mock_get:
            self._authed_client().get_user_round_details("789")

        url = mock_get.call_args[0][0]
        assert "/api/scores/getScoreDetails" in url
        assert "scoreId=789" in url

    def test_api_call_without_token_raises_auth_error(self):
        client = GolfCanadaClient()
        with pytest.raises(GolfCanadaAuthError):
            client.get_user_profile("123")

    def test_api_response_is_json_string(self):
        with patch("requests.get", side_effect=_mock_get_ok):
            result = self._authed_client().get_user_profile("1")

        parsed = json.loads(result)
        assert parsed == {"data": "ok"}


# ---------------------------------------------------------------------------
# Unit tests — client_from_env
# ---------------------------------------------------------------------------


class TestClientFromEnv:
    def test_uses_token_env_var(self, monkeypatch):
        monkeypatch.setenv("GOLF_CANADA_TOKEN", "env_token")
        monkeypatch.delenv("GOLFCANADA_USERNAME", raising=False)
        client = client_from_env()
        assert client._token == "env_token"

    def test_uses_username_password_when_no_token(self, monkeypatch):
        monkeypatch.delenv("GOLF_CANADA_TOKEN", raising=False)
        monkeypatch.setenv("GOLFCANADA_USERNAME", "u")
        monkeypatch.setenv("GOLFCANADA_PASSWORD", "p")
        with patch("requests.post", side_effect=_mock_post_ok):
            client = client_from_env()
        assert client._token == "fake_access_token"

    def test_returns_empty_client_when_no_env_vars(self, monkeypatch):
        monkeypatch.delenv("GOLF_CANADA_TOKEN", raising=False)
        monkeypatch.delenv("GOLFCANADA_USERNAME", raising=False)
        monkeypatch.delenv("GOLFCANADA_PASSWORD", raising=False)
        client = client_from_env()
        assert client._token is None


# ---------------------------------------------------------------------------
# Integration tests — require real credentials in the environment
# ---------------------------------------------------------------------------

_integration_creds = pytest.mark.skipif(
    not (os.getenv("GOLFCANADA_USERNAME") and os.getenv("GOLFCANADA_PASSWORD")),
    reason="GOLFCANADA_USERNAME and GOLFCANADA_PASSWORD not set",
)


@_integration_creds
def test_integration_login():
    """Verify that real credentials produce a valid token from Golf Canada."""
    username = os.environ["GOLFCANADA_USERNAME"]
    password = os.environ["GOLFCANADA_PASSWORD"]

    client = GolfCanadaClient()
    token = client.login(username, password)

    assert token.access_token, "Expected a non-empty access token"
    assert token.token_type.lower() == "bearer"
    assert token.expires_in > 0


@_integration_creds
def test_integration_refresh():
    """Verify that a refresh_token grant returns a new access token."""
    username = os.environ["GOLFCANADA_USERNAME"]
    password = os.environ["GOLFCANADA_PASSWORD"]

    client = GolfCanadaClient()
    original = client.login(username, password)
    refreshed = client.refresh(password)

    assert refreshed.access_token, "Expected a non-empty refreshed access token"


@_integration_creds
def test_integration_get_user_profile():
    """Verify connectivity to the Golf Canada API after login."""
    username = os.environ["GOLFCANADA_USERNAME"]
    password = os.environ["GOLFCANADA_PASSWORD"]

    client = GolfCanadaClient()
    token = client.login(username, password)

    individual_id = str(token.user.get("id", ""))
    assert individual_id, "Expected user id in token response"

    result = client.get_user_profile(individual_id)
    data = json.loads(result)
    assert data, "Expected non-empty profile response"
