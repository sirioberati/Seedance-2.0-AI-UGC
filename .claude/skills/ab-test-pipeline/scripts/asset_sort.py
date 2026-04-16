#!/usr/bin/env python3
"""
Asset Sort — Move, rename, and register images.
Moves images from inbox (or any path) into the structured asset library.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
ASSETS_DIR = BASE_DIR / "assets"
REGISTRY_PATH = ASSETS_DIR / "registry.json"
BACKUPS_DIR = ASSETS_DIR / "backups"

CATEGORY_DIRS = {
    "product": "products",
    "subject": "subjects",
    "mood": "moods",
}


def get_image_dimensions(filepath):
    """Get image dimensions using sips on macOS."""
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


def load_registry():
    """Load or initialize registry."""
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {"version": 1, "updated_at": None, "products": {}, "subjects": {}, "moods": {}}


def save_registry(registry):
    """Save registry with updated timestamp."""
    registry["updated_at"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def get_next_number(target_dir, slug, asset_type):
    """Find the next available number for naming."""
    existing = list(target_dir.glob(f"{slug}-{asset_type}-*"))
    if not existing:
        return 1
    numbers = []
    for f in existing:
        stem = f.stem
        parts = stem.rsplit("-", 1)
        if len(parts) == 2:
            try:
                numbers.append(int(parts[1]))
            except ValueError:
                pass
    return max(numbers, default=0) + 1


def sort_asset(file_path, asset_type, slug, name, description=""):
    """Move and rename a file into the asset library."""
    source = Path(file_path)
    if not source.exists():
        print(f"ERROR: File not found: {source}")
        sys.exit(1)

    if asset_type not in CATEGORY_DIRS:
        print(f"ERROR: Invalid type '{asset_type}'. Use: product, subject, mood")
        sys.exit(1)

    # Normalize slug
    slug = slug.lower().strip().replace(" ", "-").replace("_", "-")

    # Target directory
    category_dir = CATEGORY_DIRS[asset_type]
    target_dir = ASSETS_DIR / category_dir / slug
    target_dir.mkdir(parents=True, exist_ok=True)

    # Get next number and build new filename
    next_num = get_next_number(target_dir, slug, asset_type)
    ext = source.suffix.lower()
    new_filename = f"{slug}-{asset_type}-{next_num:02d}{ext}"
    target_path = target_dir / new_filename

    # Get dimensions before moving
    dimensions = get_image_dimensions(source)
    original_name = source.name

    # Backup original before moving
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUPS_DIR / f"{slug}-{original_name}"
    if backup_path.exists():
        stem = backup_path.stem
        bext = backup_path.suffix
        i = 1
        while backup_path.exists():
            backup_path = BACKUPS_DIR / f"{stem}-{i}{bext}"
            i += 1
    shutil.copy2(str(source), str(backup_path))

    # Move file
    shutil.move(str(source), str(target_path))
    print(f"Moved: {original_name} -> {target_path.relative_to(BASE_DIR)}")

    # Update registry
    registry = load_registry()
    category_key = category_dir  # "products", "subjects", "moods"

    if slug not in registry[category_key]:
        registry[category_key][slug] = {
            "name": name,
            "description": description,
            "images": [],
        }
    elif description and not registry[category_key][slug].get("description"):
        registry[category_key][slug]["description"] = description

    registry[category_key][slug]["images"].append({
        "path": str(target_path.relative_to(BASE_DIR)),
        "original_name": original_name,
        "dimensions": dimensions,
        "added_at": datetime.now().isoformat(),
    })

    save_registry(registry)
    print(f"Registry updated: {slug} ({category_key})")

    # Return info for Claude
    print(f"\n---RESULT---")
    result = {
        "slug": slug,
        "name": name,
        "type": asset_type,
        "category": category_key,
        "new_path": str(target_path.relative_to(BASE_DIR)),
        "original_name": original_name,
        "dimensions": dimensions,
    }
    print(json.dumps(result, indent=2))


def batch_sort(file_paths, asset_type, slug, name, description=""):
    """Sort multiple files into the same category."""
    for fp in file_paths:
        sort_asset(fp, asset_type, slug, name, description)
        print()


def main():
    parser = argparse.ArgumentParser(description="Sort and register an image asset")
    parser.add_argument("--file", required=True, help="Path to image file (absolute or relative to project root)")
    parser.add_argument("--type", required=True, choices=["product", "subject", "mood"],
                        help="Asset type: product, subject, or mood")
    parser.add_argument("--slug", required=True, help="URL-safe identifier (e.g., 'ag1', 'sarah', 'morning-wellness')")
    parser.add_argument("--name", required=True, help="Display name (e.g., 'AG1', 'Sarah', 'Morning Wellness')")
    parser.add_argument("--description", default="", help="Brief description of the asset")

    args = parser.parse_args()

    # Resolve file path
    file_path = args.file
    if not os.path.isabs(file_path):
        file_path = str(BASE_DIR / file_path)

    sort_asset(file_path, args.type, args.slug, args.name, args.description)


if __name__ == "__main__":
    main()
