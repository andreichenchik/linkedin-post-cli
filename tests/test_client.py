"""Unit tests for LinkedInClient and CLI."""

from unittest.mock import MagicMock, patch

import pytest

from linkedin.cli import main
from linkedin.client import LinkedInClient


@pytest.fixture
def client() -> LinkedInClient:
    return LinkedInClient(access_token="fake-token")


class TestGetUserId:
    def test_returns_sub_from_userinfo(self, client: LinkedInClient) -> None:
        with patch.object(client._session, "get") as mock_get:
            mock_get.return_value = _ok_response({"sub": "abc123"})
            assert client.get_user_id() == "abc123"

    def test_caches_user_id(self, client: LinkedInClient) -> None:
        with patch.object(client._session, "get") as mock_get:
            mock_get.return_value = _ok_response({"sub": "abc123"})
            client.get_user_id()
            client.get_user_id()
            mock_get.assert_called_once()

    def test_raises_on_http_error(self, client: LinkedInClient) -> None:
        with patch.object(client._session, "get") as mock_get:
            mock_get.return_value = _error_response(401)
            with pytest.raises(Exception):
                client.get_user_id()


class TestCreatePost:
    def test_sends_correct_body(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _created_response("urn:li:share:123")
            client.create_post("Hello!")

            body = mock_post.call_args.kwargs["json"]
            assert body["author"] == "urn:li:person:u1"
            assert body["commentary"] == "Hello!"
            assert body["lifecycleState"] == "PUBLISHED"
            assert body["visibility"] == "PUBLIC"

    def test_sends_required_headers(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _created_response("urn:li:share:123")
            client.create_post("Hi")

            headers = mock_post.call_args.kwargs["headers"]
            assert headers["LinkedIn-Version"] == "202504"
            assert headers["X-Restli-Protocol-Version"] == "2.0.0"

    def test_returns_post_urn(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _created_response("urn:li:share:456")
            assert client.create_post("test") == "urn:li:share:456"

    def test_connections_only_sets_visibility(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _created_response("urn:li:share:789")
            client.create_post("Private", connections_only=True)

            body = mock_post.call_args.kwargs["json"]
            assert body["visibility"] == "CONNECTIONS"

    def test_raises_on_api_error(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _error_response(403)
            with pytest.raises(Exception):
                client.create_post("nope")



class TestCLIValidation:
    def test_rejects_text_over_3000_chars(self) -> None:
        long_text = "a" * 3001
        with pytest.raises(SystemExit):
            main([long_text])

    def test_rejects_empty_text(self) -> None:
        with pytest.raises(SystemExit), patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = ""
            main([])


# --- helpers ---

def _ok_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _created_response(post_urn: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 201
    resp.headers = {"x-restli-id": post_urn}
    resp.raise_for_status.return_value = None
    return resp


def _error_response(status_code: int) -> MagicMock:
    from requests.exceptions import HTTPError

    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = False
    resp.text = "error"
    resp.raise_for_status.side_effect = HTTPError(response=resp)
    return resp
