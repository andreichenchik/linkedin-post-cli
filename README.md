# linkedin-post-cli

CLI utility for publishing posts to LinkedIn via the official API.

## Install

```bash
uvx linkedin-post-cli@latest "Hello world!"   # run directly
uv tool install linkedin-post-cli              # install globally
```

## Prerequisites

1. Create a LinkedIn app at https://www.linkedin.com/developers/apps/new (requires a Company Page)
2. Add products: **Sign In with LinkedIn using OpenID Connect** and **Share on LinkedIn**
3. In **Auth** → Redirect URLs, add: `http://localhost:8000/callback`
4. Copy `Client ID` and `Client Secret` — you'll be prompted on first run

## Usage

```bash
# Inline text
linkedin-post-cli "My first post via API!"

# From file
linkedin-post-cli --from-file draft.txt

# Interactive input (multiline, Ctrl+D to send)
linkedin-post-cli

# Visible to connections only
linkedin-post-cli --connections-only "Private update"

# Attach an image
linkedin-post-cli --image photo.jpg "Check this out!"

# Re-authorize (clear OAuth token)
linkedin-post-cli --reset-auth "Hello again"

# Clear all saved credentials
linkedin-post-cli --reset-keys "Starting over"
```

On first run, you'll be prompted for Client ID and Client Secret, then a browser window opens for OAuth authorization. Credentials are saved to `~/.config/linkedin-post-cli/config.json`.

## Tests

```bash
uv run pytest -v
```
