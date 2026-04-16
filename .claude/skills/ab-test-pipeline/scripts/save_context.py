#!/usr/bin/env python3
"""
Save AI context for an image in the registry.
Called by Claude CLI after analyzing an image with vision.

Usage:
  python3 save_context.py --path "assets/products/ag1/ag1-product-01.png" --context '{"product_type":"supplement",...}'
"""

import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
REGISTRY_PATH = BASE_DIR / "assets" / "registry.json"


def save_context(image_path, context_json):
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    # Parse context
    if isinstance(context_json, str):
        context = json.loads(context_json)
    else:
        context = context_json

    updated = False
    for cat in ["products", "subjects", "moods"]:
        for slug, data in registry.get(cat, {}).items():
            for img in data.get("images", []):
                if img["path"] == image_path:
                    img["ai_context"] = context
                    updated = True
                    break

    if updated:
        from datetime import datetime
        registry["updated_at"] = datetime.now().isoformat()
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2)
        print(f"Context saved for: {image_path}")
    else:
        print(f"ERROR: Image not found in registry: {image_path}")


def list_unanalyzed():
    """List all images that don't have ai_context yet."""
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    pending = []
    for cat in ["products", "subjects", "moods"]:
        asset_type = cat.rstrip("s")  # products -> product
        for slug, data in registry.get(cat, {}).items():
            for img in data.get("images", []):
                if not img.get("ai_context"):
                    pending.append({
                        "path": img["path"],
                        "type": asset_type,
                        "slug": slug,
                        "name": data.get("name", slug),
                    })

    if not pending:
        print("All images have AI context.")
    else:
        print(f"{len(pending)} image(s) need analysis:\n")
        for p in pending:
            print(f"  [{p['type']}] {p['path']}")

    # Output JSON for Claude to parse
    print(f"\n---JSON---")
    print(json.dumps(pending, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Save AI context for registry images")
    sub = parser.add_subparsers(dest="command")

    save_p = sub.add_parser("save", help="Save context for an image")
    save_p.add_argument("--path", required=True, help="Image path in registry")
    save_p.add_argument("--context", required=True, help="JSON string of AI context")

    sub.add_parser("pending", help="List images without AI context")

    args = parser.parse_args()
    if args.command == "save":
        save_context(args.path, args.context)
    elif args.command == "pending":
        list_unanalyzed()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
