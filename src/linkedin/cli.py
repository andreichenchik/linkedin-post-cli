"""CLI entry-point for linkedin-post."""

import argparse
import pathlib
import sys

import dotenv

from linkedin.auth import authenticate, is_token_valid
from linkedin.client import LinkedInClient

_ENV_PATH = pathlib.Path.cwd() / ".env"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a text post to LinkedIn.",
    )
    parser.add_argument("text", nargs="?", help="Post text (inline)")
    parser.add_argument(
        "--from-file", type=pathlib.Path, help="Read post text from a file"
    )
    parser.add_argument(
        "--connections-only",
        action="store_true",
        help="Visible to 1st-degree connections only (default: public)",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Force re-authorization even if a token exists",
    )
    return parser.parse_args(argv)


def _read_post_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.from_file:
        return args.from_file.read_text(encoding="utf-8").strip()
    print("Enter post text (Ctrl+D to send):")
    return sys.stdin.read().strip()


def _ensure_token(
    client_id: str, client_secret: str, existing_token: str | None, force: bool
) -> str:
    """Return a valid access token, running OAuth if needed."""
    if not force and existing_token and is_token_valid(existing_token):
        return existing_token

    token = authenticate(client_id, client_secret)
    dotenv.set_key(str(_ENV_PATH), "ACCESS_TOKEN", token)
    return token


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    dotenv.load_dotenv(_ENV_PATH)

    import os

    client_id = os.getenv("CLIENT_ID", "")
    client_secret = os.getenv("CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "CLIENT_ID and CLIENT_SECRET must be set in .env",
            file=sys.stderr,
        )
        sys.exit(1)

    token = _ensure_token(
        client_id,
        client_secret,
        os.getenv("ACCESS_TOKEN"),
        force=args.auth,
    )

    max_length = 3000
    text = _read_post_text(args)
    if not text:
        print("Empty post text, aborting.", file=sys.stderr)
        sys.exit(1)
    if len(text) > max_length:
        print(
            f"Post too long: {len(text)}/{max_length} characters.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = LinkedInClient(token)
    post_urn = client.create_post(text, connections_only=args.connections_only)
    post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
    visibility = "connections only" if args.connections_only else "public"
    print(f"Post published ({visibility})!")
    print(post_url)
