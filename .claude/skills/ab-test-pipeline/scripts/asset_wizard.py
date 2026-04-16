#!/usr/bin/env python3
"""
Asset Wizard — Scanner
Scans the inbox folder for new images and reports metadata.
Also provides registry listing and status commands.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
ASSETS_DIR = BASE_DIR / "assets"
INBOX_DIR = ASSETS_DIR / "inbox"
REGISTRY_PATH = ASSETS_DIR / "registry.json"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def get_image_dimensions(filepath):
    """Get image dimensions without PIL — uses sips on macOS."""
    import subprocess
    try:
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(filepath)],
            capture_output=True, text=True, timeout=5
        )
        width = height = "?"
        for line in result.stdout.splitlines():
            if "pixelWidth" in line:
                width = line.split(":")[-1].strip()
            if "pixelHeight" in line:
                height = line.split(":")[-1].strip()
        return f"{width}x{height}"
    except Exception:
        return "unknown"


def scan_inbox():
    """Scan inbox for new images and report metadata."""
    if not INBOX_DIR.exists():
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        print("Created assets/inbox/ — drop your images there and run again.")
        return

    images = []
    for f in sorted(INBOX_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and f.name != ".gitkeep":
            size_mb = f.stat().st_size / (1024 * 1024)
            dims = get_image_dimensions(f)
            images.append({
                "filename": f.name,
                "path": str(f),
                "relative_path": str(f.relative_to(BASE_DIR)),
                "size_mb": round(size_mb, 2),
                "dimensions": dims,
                "extension": f.suffix.lower(),
            })

    if not images:
        print("Inbox is empty.")
        print(f"Drop images into: {INBOX_DIR}")
        print("Then run `/assets` again.")
        return

    print(f"Found {len(images)} image(s) in assets/inbox/:\n")
    print(f"  {'#':<4} {'FILENAME':<35} {'SIZE':<10} {'DIMENSIONS':<15} {'PATH'}")
    print(f"  {'-'*4} {'-'*35} {'-'*10} {'-'*15} {'-'*40}")

    for i, img in enumerate(images, 1):
        print(f"  {i:<4} {img['filename']:<35} {img['size_mb']:.1f} MB    {img['dimensions']:<15} {img['relative_path']}")

    # Output as JSON for Claude to parse
    print(f"\n---JSON---")
    print(json.dumps(images, indent=2))


def show_registry():
    """Display the current asset registry."""
    if not REGISTRY_PATH.exists():
        print("No registry found. Run `/assets` to get started.")
        return

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    print("Asset Library Registry")
    print(f"Updated: {registry.get('updated_at', 'never')}\n")

    for category in ["products", "subjects", "moods"]:
        items = registry.get(category, {})
        label = category.upper()
        print(f"{label} ({len(items)} total)")
        if not items:
            print("  (empty)\n")
            continue
        for slug, data in items.items():
            img_count = len(data.get("images", []))
            desc = data.get("description", "")[:50]
            print(f"  {slug:<20} — {img_count} image(s) — {desc}")
        print()

    # Total counts
    total = sum(
        len(data.get("images", []))
        for cat in ["products", "subjects", "moods"]
        for data in registry.get(cat, {}).values()
    )
    print(f"Total assets: {total}")


def main():
    parser = argparse.ArgumentParser(description="Asset Wizard Scanner")
    parser.add_argument("command", choices=["scan", "registry", "status"],
                        help="scan: check inbox | registry/status: show library")
    args = parser.parse_args()

    if args.command == "scan":
        scan_inbox()
    elif args.command in ("registry", "status"):
        show_registry()


if __name__ == "__main__":
    main()
