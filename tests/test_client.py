"""Unit tests for LinkedInClient and CLI."""

import pathlib
from unittest.mock import MagicMock, patch

import pytest

from linkedin.cli import main
from linkedin.client import LinkedInClient, _MAX_IMAGE_SIZE


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



class TestUploadImage:
    def test_returns_image_urn(self, client: LinkedInClient, tmp_path: pathlib.Path) -> None:
        img = tmp_path / "photo.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 100)

        init_resp = _ok_response({
            "value": {
                "uploadUrl": "https://linkedin.com/upload/xyz",
                "image": "urn:li:image:C123",
            }
        })
        put_resp = MagicMock(ok=True)

        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post", return_value=init_resp),
            patch.object(client._session, "put", return_value=put_resp),
        ):
            urn = client.upload_image(img)

        assert urn == "urn:li:image:C123"

    def test_rejects_unsupported_format(
        self, client: LinkedInClient, tmp_path: pathlib.Path
    ) -> None:
        img = tmp_path / "photo.bmp"
        img.write_bytes(b"\x00" * 10)

        with pytest.raises(ValueError, match="Unsupported image format"):
            client.upload_image(img)

    def test_rejects_oversized_file(
        self, client: LinkedInClient, tmp_path: pathlib.Path
    ) -> None:
        img = tmp_path / "huge.png"
        img.write_bytes(b"\x00" * (_MAX_IMAGE_SIZE + 1))

        with pytest.raises(ValueError, match="Image too large"):
            client.upload_image(img)

    def test_raises_on_init_upload_error(
        self, client: LinkedInClient, tmp_path: pathlib.Path
    ) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(
                client._session, "post", return_value=_error_response(500)
            ),
        ):
            with pytest.raises(Exception):
                client.upload_image(img)

    def test_raises_on_upload_error(
        self, client: LinkedInClient, tmp_path: pathlib.Path
    ) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        init_resp = _ok_response({
            "value": {
                "uploadUrl": "https://linkedin.com/upload/xyz",
                "image": "urn:li:image:C123",
            }
        })
        put_resp = _error_response(500)

        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post", return_value=init_resp),
            patch.object(client._session, "put", return_value=put_resp),
        ):
            with pytest.raises(Exception):
                client.upload_image(img)


class TestCreatePostWithImage:
    def test_includes_image_content_in_body(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _created_response("urn:li:share:999")
            client.create_post("With image", image_urn="urn:li:image:C123")

            body = mock_post.call_args.kwargs["json"]
            assert body["content"] == {"media": {"id": "urn:li:image:C123"}}

    def test_omits_content_when_no_image(self, client: LinkedInClient) -> None:
        with (
            patch.object(
                client._session, "get", return_value=_ok_response({"sub": "u1"})
            ),
            patch.object(client._session, "post") as mock_post,
        ):
            mock_post.return_value = _created_response("urn:li:share:999")
            client.create_post("Text only")

            body = mock_post.call_args.kwargs["json"]
            assert "content" not in body


class TestCLIValidation:
    def test_rejects_text_over_3000_chars(self) -> None:
        long_text = "a" * 3001
        with pytest.raises(SystemExit):
            main([long_text])

    def test_rejects_empty_text(self) -> None:
        with pytest.raises(SystemExit), patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = ""
            main([])


class TestCLIImage:
    def test_passes_image_urn_to_create_post(self, tmp_path: pathlib.Path) -> None:
        img = tmp_path / "pic.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.upload_image.return_value = "urn:li:image:ABC"
        mock_client.create_post.return_value = "urn:li:share:999"

        with (
            patch("linkedin.cli.LinkedInClient", return_value=mock_client),
            patch("linkedin.cli._ensure_token", return_value="tok"),
            patch("linkedin.cli.dotenv"),
            patch.dict("os.environ", {"CLIENT_ID": "id", "CLIENT_SECRET": "sec"}),
        ):
            main(["Hello", "--image", str(img)])

        mock_client.upload_image.assert_called_once_with(img)
        mock_client.create_post.assert_called_once_with(
            "Hello", connections_only=False, image_urn="urn:li:image:ABC"
        )

    def test_exits_when_image_not_found(self) -> None:
        with (
            patch("linkedin.cli._ensure_token", return_value="tok"),
            patch("linkedin.cli.dotenv"),
            patch.dict("os.environ", {"CLIENT_ID": "id", "CLIENT_SECRET": "sec"}),
            pytest.raises(SystemExit),
        ):
            main(["Hello", "--image", "/nonexistent/photo.png"])


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
