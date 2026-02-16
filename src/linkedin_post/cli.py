"""CLI entry-point for linkedin-post-cli."""

import argparse
import pathlib
import sys

from linkedin_post.auth import authenticate, is_token_valid
from linkedin_post.client import LinkedInClient
from linkedin_post.config import ConfigStore, JsonConfigStore, prompt_if_missing

_MAX_LENGTH = 3000


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a text post to LinkedIn.",
    )
    parser.add_argument("text", nargs="?", help="Post text (inline)")
    parser.add_argument(
        "--from-file", type=pathlib.Path, help="Read post text from a file",
    )
    parser.add_argument(
        "--connections-only",
        action="store_true",
        help="Visible to 1st-degree connections only (default: public)",
    )
    parser.add_argument(
        "--image",
        type=pathlib.Path,
        metavar="PATH",
        help="Attach an image (jpg/png/gif, max 100 MB)",
    )
    parser.add_argument(
        "--reset-auth",
        action="store_true",
        help="Clear saved OAuth token and re-authorize",
    )
    parser.add_argument(
        "--reset-keys",
        action="store_true",
        help="Clear all saved credentials and re-prompt from scratch",
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
    config: ConfigStore,
    client_id: str,
    client_secret: str,
    *,
    force: bool,
) -> str:
    """Return a valid access token, running OAuth if needed."""
    access_token = config.get("access_token")

    if not force and access_token and is_token_valid(access_token):
        return access_token

    token = authenticate(client_id, client_secret)
    config.set("access_token", token)
    return token


def main(argv: list[str] | None = None, *, _config: ConfigStore | None = None) -> None:
    args = _parse_args(argv)
    config = _config or JsonConfigStore()

    if args.reset_keys:
        config.remove(["client_id", "client_secret", "access_token"])
    elif args.reset_auth:
        config.remove(["access_token"])

    if not config.get("client_id"):
        print(
            "\n"
            "First-time setup\n"
            "================\n"
            "You need OAuth 2.0 credentials from the LinkedIn Developer Portal.\n"
            "\n"
            "1. Create an app at https://www.linkedin.com/developers/apps/new\n"
            "   (requires a Company Page)\n"
            "2. Add products: Sign In with LinkedIn using OpenID Connect\n"
            "   and Share on LinkedIn\n"
            "3. In Auth → Redirect URLs, add: http://localhost:8000/callback\n"
            "4. Copy the Client ID and Client Secret below\n",
        )

    client_id = prompt_if_missing(config, "client_id", "Client ID")
    client_secret = prompt_if_missing(config, "client_secret", "Client Secret")

    text = _read_post_text(args)
    if not text:
        print("Empty post text, aborting.", file=sys.stderr)
        sys.exit(1)
    if len(text) > _MAX_LENGTH:
        print(
            f"Post too long: {len(text)}/{_MAX_LENGTH} characters.",
            file=sys.stderr,
        )
        sys.exit(1)

    access_token = _ensure_token(
        config, client_id, client_secret,
        force=args.reset_auth,
    )

    client = LinkedInClient(access_token)

    image_urn = None
    if args.image:
        if not args.image.exists():
            print(f"Image not found: {args.image}", file=sys.stderr)
            sys.exit(1)
        try:
            image_urn = client.upload_image(args.image)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)

    post_urn = client.create_post(
        text, connections_only=args.connections_only, image_urn=image_urn,
    )
    post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
    visibility = "connections only" if args.connections_only else "public"
    print(f"Post published ({visibility})!")
    print(post_url)
