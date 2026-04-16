#!/usr/bin/env python3
"""
Onboarding — Brand Profile Manager
Saves, loads, and lists brand profiles in config/brands.json.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
BRANDS_PATH = BASE_DIR / "config" / "brands.json"


def load_brands():
    """Load or initialize brands.json."""
    if BRANDS_PATH.exists():
        with open(BRANDS_PATH) as f:
            return json.load(f)
    return {"version": 1, "brands": {}}


def save_brands(data):
    """Save brands.json."""
    BRANDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BRANDS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def save_brand(args):
    """Save a brand profile."""
    data = load_brands()

    slug = args.slug.lower().strip().replace(" ", "-")
    selling_points = [sp.strip() for sp in args.selling_points.split(",")] if args.selling_points else []
    platforms = [p.strip() for p in args.platforms.split(",")] if args.platforms else []
    competitors = [c.strip() for c in args.competitors.split(",")] if args.competitors else []

    brand = {
        "name": args.name,
        "slug": slug,
        "category": args.category or "",
        "description": args.description or "",
        "selling_points": selling_points,
        "price_point": args.price_point or "$$",
        "differentiator": args.differentiator or "",
        "audience": {
            "age_range": args.age_range or "18-65",
            "gender": args.gender or "All",
            "interests": args.interests or "",
        },
        "goals": {
            "objective": args.objective or "Conversion",
            "platforms": platforms,
            "tone": args.tone or "Casual/Fun",
        },
        "competitors": competitors,
        "discount_code": args.discount_code or "",
        "discount_details": args.discount_details or "",
        "custom_notes": args.custom_notes or "",
        "custom_cta": args.custom_cta or "",
        "created_at": datetime.now().isoformat(),
    }

    data["brands"][slug] = brand
    save_brands(data)

    print(f"Brand saved: {brand['name']} ({slug})")
    print(f"Config: {BRANDS_PATH}")
    print()
    print(f"---BRAND---")
    print(json.dumps(brand, indent=2))


def list_brands():
    """List all brand profiles."""
    data = load_brands()
    brands = data.get("brands", {})

    if not brands:
        print("No brands configured yet.")
        print("Run /onboard to set up your first product.")
        return

    print(f"{'BRAND':<20} {'CATEGORY':<15} {'AUDIENCE':<25} {'GOAL':<15} {'PLATFORMS'}")
    print("-" * 95)
    for slug, brand in brands.items():
        audience = brand.get("audience", {})
        goals = brand.get("goals", {})
        age = audience.get("age_range", "?")
        platforms = ", ".join(goals.get("platforms", []))
        print(f"{brand['name']:<20} {brand.get('category', ''):<15} {age:<25} {goals.get('objective', ''):<15} {platforms}")

    print(f"\nTotal: {len(brands)} brand(s)")


def get_brand(slug):
    """Get a single brand profile."""
    data = load_brands()
    brand = data.get("brands", {}).get(slug)
    if not brand:
        print(f"Brand '{slug}' not found.")
        list_brands()
        return
    print(json.dumps(brand, indent=2))


def delete_brand(slug):
    """Delete a brand profile."""
    data = load_brands()
    if slug in data.get("brands", {}):
        name = data["brands"][slug]["name"]
        del data["brands"][slug]
        save_brands(data)
        print(f"Deleted brand: {name} ({slug})")
    else:
        print(f"Brand '{slug}' not found.")


def main():
    parser = argparse.ArgumentParser(description="Brand Profile Manager")
    sub = parser.add_subparsers(dest="command")

    # Save
    save_parser = sub.add_parser("save", help="Save a brand profile")
    save_parser.add_argument("--slug", required=True)
    save_parser.add_argument("--name", required=True)
    save_parser.add_argument("--category", default="")
    save_parser.add_argument("--description", default="")
    save_parser.add_argument("--selling-points", default="")
    save_parser.add_argument("--price-point", default="$$")
    save_parser.add_argument("--differentiator", default="")
    save_parser.add_argument("--age-range", default="18-65")
    save_parser.add_argument("--gender", default="All")
    save_parser.add_argument("--interests", default="")
    save_parser.add_argument("--objective", default="Conversion")
    save_parser.add_argument("--platforms", default="")
    save_parser.add_argument("--tone", default="Casual/Fun")
    save_parser.add_argument("--competitors", default="")
    save_parser.add_argument("--discount-code", default="")
    save_parser.add_argument("--discount-details", default="")
    save_parser.add_argument("--custom-notes", default="")
    save_parser.add_argument("--custom-cta", default="")

    # List
    sub.add_parser("list", help="List all brand profiles")

    # Get
    get_parser = sub.add_parser("get", help="Get a brand profile")
    get_parser.add_argument("slug")

    # Delete
    del_parser = sub.add_parser("delete", help="Delete a brand profile")
    del_parser.add_argument("slug")

    args = parser.parse_args()

    if args.command == "save":
        save_brand(args)
    elif args.command == "list":
        list_brands()
    elif args.command == "get":
        get_brand(args.slug)
    elif args.command == "delete":
        delete_brand(args.slug)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
