"""LinkedIn API client for creating posts."""

import pathlib
from typing import Protocol

import requests

_BASE_URL = "https://api.linkedin.com"
_LINKEDIN_VERSION = "202504"
_SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif"}
_MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB — LinkedIn documented limit

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


class LinkedInAPI(Protocol):
    """Interface for LinkedIn API operations."""

    def get_user_id(self) -> str:
        """Return the authenticated user's person ID."""
        ...

    def upload_image(self, path: pathlib.Path) -> str:
        """Upload an image and return the image URN."""
        ...

    def create_post(
        self, text: str, *, connections_only: bool = False, image_urn: str | None = None
    ) -> str:
        """Publish a post and return the post URN."""
        ...


class LinkedInClient:
    """HTTP client for LinkedIn REST API.

    Usage::

        client = LinkedInClient(access_token="...")
        post_urn = client.create_post("Hello LinkedIn!")
    """

    def __init__(self, access_token: str) -> None:
        self._token = access_token
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {access_token}",
        })
        self._user_id: str | None = None

    def get_user_id(self) -> str:
        """Return the authenticated user's person ID (``sub`` claim)."""
        if self._user_id is None:
            resp = self._session.get(f"{_BASE_URL}/v2/userinfo")
            resp.raise_for_status()
            self._user_id = resp.json()["sub"]
        return self._user_id

    def upload_image(self, path: pathlib.Path) -> str:
        """Upload an image file and return the image URN.

        Raises ``ValueError`` for unsupported formats or oversized files.
        """
        suffix = path.suffix.lower()
        if suffix not in _SUPPORTED_IMAGE_TYPES:
            raise ValueError(
                f"Unsupported image format '{suffix}'. "
                f"Supported: {', '.join(sorted(_SUPPORTED_IMAGE_TYPES))}"
            )
        file_size = path.stat().st_size
        if file_size > _MAX_IMAGE_SIZE:
            raise ValueError(
                f"Image too large: {file_size} bytes "
                f"(max {_MAX_IMAGE_SIZE} bytes / 100 MB)"
            )

        owner = f"urn:li:person:{self.get_user_id()}"
        init_resp = self._session.post(
            f"{_BASE_URL}/rest/images?action=initializeUpload",
            json={"initializeUploadRequest": {"owner": owner}},
            headers={
                "LinkedIn-Version": _LINKEDIN_VERSION,
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        if not init_resp.ok:
            raise requests.HTTPError(
                f"{init_resp.status_code}: {init_resp.text}", response=init_resp
            )
        data = init_resp.json()["value"]
        upload_url = data["uploadUrl"]
        image_urn = data["image"]

        put_resp = self._session.put(
            upload_url,
            data=path.read_bytes(),
            headers={"Content-Type": _CONTENT_TYPES[suffix]},
        )
        if not put_resp.ok:
            raise requests.HTTPError(
                f"{put_resp.status_code}: {put_resp.text}", response=put_resp
            )
        return image_urn

    def create_post(
        self, text: str, *, connections_only: bool = False, image_urn: str | None = None
    ) -> str:
        """Publish a post, optionally with an image. Returns the created post URN."""
        author = f"urn:li:person:{self.get_user_id()}"
        visibility = "CONNECTIONS" if connections_only else "PUBLIC"
        body: dict = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "visibility": visibility,
            "commentary": text,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
        }
        if image_urn is not None:
            body["content"] = {"media": {"id": image_urn}}
        resp = self._session.post(
            f"{_BASE_URL}/rest/posts",
            json=body,
            headers={
                "LinkedIn-Version": _LINKEDIN_VERSION,
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        if not resp.ok:
            raise requests.HTTPError(
                f"{resp.status_code}: {resp.text}", response=resp
            )
        return resp.headers.get("x-restli-id", "")
