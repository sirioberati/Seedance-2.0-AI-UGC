#!/usr/bin/env python3
"""
UGC Ad Pipeline — First-time setup.
Fetches project configuration from the gateway API.
"""

import json
import os
import shutil
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
API_URL = "https://gateway.sirioberati.com/.netlify/functions/generate-prompts"


def fetch_text(endpoint):
    """Fetch text content from the gateway API."""
    url = f"{API_URL}{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  Error fetching {endpoint}: {e}")
        return None


def setup():
    print("UGC Ad Pipeline — Setup\n")

    # 1. Fetch CLAUDE.md
    print("Fetching project configuration...")
    claude_md = fetch_text("/claude-md")
    if claude_md:
        with open(BASE_DIR / "CLAUDE.md", "w") as f:
            f.write(claude_md)
        print("  CLAUDE.md written")
    else:
        print("  WARNING: Could not fetch CLAUDE.md — check your internet connection")

    # 2. README.md ships with the repo — no need to fetch

    # 3. Create .env from example if it doesn't exist
    env_path = BASE_DIR / ".env"
    env_example = BASE_DIR / ".env.example"
    if not env_path.exists() and env_example.exists():
        shutil.copy2(str(env_example), str(env_path))
        print("  .env created from .env.example — add your ENHANCOR_API_KEY")
    elif env_path.exists():
        print("  .env already exists")

    # 4. Create directories
    for d in ["assets/inbox", "assets/products", "assets/subjects", "assets/moods", "assets/backups", "projects", "config"]:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)

    # 5. Create registry.json if missing
    reg_path = BASE_DIR / "assets" / "registry.json"
    if not reg_path.exists():
        with open(reg_path, "w") as f:
            json.dump({"version": 1, "updated_at": None, "products": {}, "subjects": {}, "moods": {}, "audio": {}}, f, indent=2)
        print("  assets/registry.json created")

    # 6. Create brands.json if missing
    brands_path = BASE_DIR / "config" / "brands.json"
    if not brands_path.exists():
        with open(brands_path, "w") as f:
            json.dump({"version": 1, "brands": {}}, f, indent=2)
        print("  config/brands.json created")

    print("\nSetup complete!")
    print("\nNext steps:")
    print("  1. Add your ENHANCOR_API_KEY to .env")
    print("  2. Open this folder in Claude Code")
    print("  3. Type /onboard to set up your product")
    print("  4. Start the Control Center: python3 .claude/skills/ab-test-pipeline/scripts/asset_server.py")


if __name__ == "__main__":
    setup()
