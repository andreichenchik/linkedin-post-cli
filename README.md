# linkedin-post

CLI utility for publishing posts to LinkedIn via the official API.

## Prerequisites

1. Create a LinkedIn app at https://www.linkedin.com/developers/apps/new (requires a Company Page)
2. Add products: **Sign In with LinkedIn using OpenID Connect** and **Share on LinkedIn**
3. In **Auth** → Redirect URLs, add: `http://localhost:8000/callback`
4. Copy `Client ID` and `Client Secret`

## Setup

```bash
cp .env.example .env
# Fill in CLIENT_ID and CLIENT_SECRET
```

## Usage

```bash
# Inline text
uv run linkedin-post "My first post via API!"

# From file
uv run linkedin-post --from-file draft.txt

# Interactive input (multiline, Ctrl+D to send)
uv run linkedin-post

# Visible to connections only
uv run linkedin-post --connections-only "Private update"

# Force re-authorization
uv run linkedin-post --auth
```

On first run, a browser window will open for OAuth authorization. The token is saved to `.env` automatically.

## Tests

```bash
uv run pytest
```
