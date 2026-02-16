"""LinkedIn API client for creating posts."""

from typing import Protocol

import requests

_BASE_URL = "https://api.linkedin.com"
_LINKEDIN_VERSION = "202504"


class LinkedInAPI(Protocol):
    """Interface for LinkedIn API operations."""

    def get_user_id(self) -> str:
        """Return the authenticated user's person ID."""
        ...

    def create_post(self, text: str, *, connections_only: bool = False) -> str:
        """Publish a text post and return the post URN."""
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

    def create_post(self, text: str, *, connections_only: bool = False) -> str:
        """Publish a text post. Returns the created post URN."""
        author = f"urn:li:person:{self.get_user_id()}"
        visibility = "CONNECTIONS" if connections_only else "PUBLIC"
        body = {
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
