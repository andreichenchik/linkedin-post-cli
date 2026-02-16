"""OAuth 2.0 authentication flow for LinkedIn."""

import http.server
import sys
import threading
import urllib.parse
import webbrowser

import requests

_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
_REDIRECT_URI = "http://localhost:8000/callback"
_SCOPES = "openid profile w_member_social"


def is_token_valid(token: str) -> bool:
    """Check whether *token* is still accepted by LinkedIn API."""
    resp = requests.get(
        _USERINFO_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return resp.status_code == 200


def authenticate(client_id: str, client_secret: str) -> str:
    """Run the full OAuth browser flow and return an access token.

    Opens the default browser for user consent, starts a temporary
    local HTTP server to capture the redirect, and exchanges the
    authorization code for a token.
    """
    auth_code: str | None = None
    error: str | None = None
    server_ready = threading.Event()

    class _CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            nonlocal auth_code, error
            params = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query
            )

            if "code" in params:
                auth_code = params["code"][0]
                self._respond("Authorization successful! You can close this tab.")
            else:
                error = params.get("error", ["unknown"])[0]
                self._respond(f"Authorization failed: {error}")

            # Shut down server from a separate thread to avoid deadlock.
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def _respond(self, message: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>{message}</h2></body></html>".encode()
            )

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # silence request logs

    server = http.server.HTTPServer(("localhost", 8000), _CallbackHandler)

    def _serve() -> None:
        server_ready.set()
        server.serve_forever()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    server_ready.wait()

    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _REDIRECT_URI,
        "scope": _SCOPES,
    })
    authorization_url = f"{_AUTH_URL}?{params}"
    print(f"Opening browser for authorization...\n{authorization_url}")
    webbrowser.open(authorization_url)

    thread.join()  # blocks until callback arrives

    if error or auth_code is None:
        print(f"Authorization failed: {error}", file=sys.stderr)
        sys.exit(1)

    token_resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": _REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    token_resp.raise_for_status()
    return token_resp.json()["access_token"]
