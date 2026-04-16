#!/usr/bin/env python3
"""
A/B Test Matrix Builder
Calls the remote prompt API to generate variants, then builds matrix.json.
"""

import argparse
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
REGISTRY_PATH = BASE_DIR / "assets" / "registry.json"
BRANDS_PATH = BASE_DIR / "config" / "brands.json"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

PROMPT_API_URL = os.environ.get(
    "PROMPT_API_URL",
    "https://gateway.sirioberati.com/.netlify/functions/generate-prompts"
)

# SSL context for compatibility
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def load_registry():
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {"products": {}, "subjects": {}, "moods": {}, "audio": {}}


def resolve_from_registry(category, slug):
    registry = load_registry()
    items = registry.get(category, {})
    if slug not in items:
        return []
    return [str(BASE_DIR / img["path"]) for img in items[slug].get("images", [])]


def get_ai_context(registry, product_slug=None, subject_slug=None, mood_slug=None):
    """Gather AI context from registry for the prompt API."""
    ctx = {}
    if product_slug:
        product = registry.get("products", {}).get(product_slug, {})
        images = product.get("images", [])
        if images and images[0].get("ai_context"):
            ctx["product"] = images[0]["ai_context"]
    if subject_slug:
        subject = registry.get("subjects", {}).get(subject_slug, {})
        images = subject.get("images", [])
        if images and images[0].get("ai_context"):
            ctx["subject"] = images[0]["ai_context"]
    if mood_slug:
        mood = registry.get("moods", {}).get(mood_slug, {})
        images = mood.get("images", [])
        if images and images[0].get("ai_context"):
            ctx["mood"] = images[0]["ai_context"]
    # Check for audio
    audio = registry.get("audio", {})
    if audio:
        first_slug = next(iter(audio), None)
        if first_slug:
            audio_imgs = audio[first_slug].get("images", [])
            if audio_imgs and audio_imgs[0].get("ai_context"):
                ctx["audio"] = audio_imgs[0]["ai_context"]
    return ctx


def load_brand(slug):
    if not BRANDS_PATH.exists():
        return None
    with open(BRANDS_PATH) as f:
        data = json.load(f)
    return data.get("brands", {}).get(slug)


def fetch_prompts(payload):
    """Call the remote prompt API to generate variants."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        PROMPT_API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("success"):
                return result.get("variants", [])
            else:
                print(f"ERROR: Prompt API returned: {result}")
                return None
    except Exception as e:
        print(f"ERROR: Could not reach prompt API at {PROMPT_API_URL}: {e}")
        return None


def build_matrix(args):
    """Build the A/B test matrix by calling the remote prompt API."""

    # Load brand profile if slug provided
    if args.brand_slug:
        brand = load_brand(args.brand_slug)
        if brand:
            print(f"Loaded brand profile: {brand['name']}")
            if not args.product:
                args.product = brand["name"]
            if not args.description:
                args.description = brand["description"]
            if not args.selling_points:
                args.selling_points = ",".join(brand.get("selling_points", []))
            if not args.audience:
                audience = brand.get("audience", {})
                args.audience = f"{audience.get('gender', 'All')} {audience.get('age_range', '18-65')}, {audience.get('interests', '')}"
            if not args.product_slug:
                args.product_slug = brand["slug"]
        else:
            print(f"WARNING: Brand '{args.brand_slug}' not found")

    selling_points = [sp.strip() for sp in args.selling_points.split(",")]

    # Resolve images from registry
    registry = load_registry()
    product_image = None
    subject_image = None
    lifestyle_images = []
    audio_path = None

    if args.product_slug:
        paths = resolve_from_registry("products", args.product_slug)
        if paths:
            product_image = paths[0]
            print(f"Product image: {product_image}")

    if not product_image and args.image:
        product_image = str(BASE_DIR / args.image)

    if args.subject_slug:
        paths = resolve_from_registry("subjects", args.subject_slug)
        if paths:
            subject_image = paths[0]
            print(f"Subject image: {subject_image}")

    if args.mood_slug:
        paths = resolve_from_registry("moods", args.mood_slug)
        if paths:
            lifestyle_images = paths[:2]

    # Check for audio in registry
    audio_reg = registry.get("audio", {})
    if audio_reg:
        first_audio_slug = next(iter(audio_reg), None)
        if first_audio_slug:
            audio_items = audio_reg[first_audio_slug].get("audio", [])
            if audio_items:
                audio_path = str(BASE_DIR / audio_items[0]["path"])

    # Gather AI context for prompt API
    ai_context = get_ai_context(registry, args.product_slug, args.subject_slug, args.mood_slug)

    # Load brand extras
    brand = load_brand(args.brand_slug or args.product_slug or "")
    discount_code = brand.get("discount_code", "") if brand else ""
    discount_details = brand.get("discount_details", "") if brand else ""
    custom_notes = brand.get("custom_notes", "") if brand else ""
    custom_cta = brand.get("custom_cta", "") if brand else ""
    tone = brand.get("goals", {}).get("tone", "Casual/Fun") if brand else "Casual/Fun"

    # Call prompt API
    print(f"Fetching prompts from API...")
    api_payload = {
        "product_name": args.product,
        "description": args.description,
        "selling_points": selling_points,
        "audience": args.audience,
        "tone": tone,
        "discount_code": discount_code,
        "discount_details": discount_details,
        "custom_notes": custom_notes,
        "custom_cta": custom_cta,
        "formats": ["podcast", "ugc", "lifestyle", "greenscreen"],
        "ai_context": ai_context,
    }

    variants = fetch_prompts(api_payload)
    if not variants:
        print("FATAL: Could not generate prompts. Check your internet connection.")
        sys.exit(1)

    print(f"Received {len(variants)} variants from API\n")

    # Create project directory
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    project_slug = args.product.lower().replace(" ", "-")
    project_dir = BASE_DIR / "projects" / f"{project_slug}-{timestamp}"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Attach image paths and status to each variant
    for v in variants:
        images = {"products": [product_image]} if product_image else {"products": []}
        if subject_image:
            images["subject"] = subject_image
        if v["format"] == "lifestyle" and lifestyle_images:
            images["references"] = lifestyle_images
        if audio_path:
            images["audio"] = audio_path

        v["images"] = images
        v["output_file"] = f"{v['id']}.mp4"
        v["status"] = "pending"
        v["generation_id"] = None
        v["error"] = None

    matrix = {
        "project": {
            "product": args.product,
            "description": args.description,
            "selling_points": selling_points,
            "audience": args.audience,
            "product_image": product_image,
            "lifestyle_images": lifestyle_images,
            "created_at": datetime.now().isoformat(),
        },
        "project_dir": str(project_dir),
        "total_variants": len(variants),
        "variants": variants,
    }

    matrix_path = project_dir / "matrix.json"
    with open(matrix_path, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"Matrix created: {matrix_path}")
    print(f"Project dir: {project_dir}")
    print(f"Total variants: {len(variants)}\n")

    print(f"{'FORMAT':<20} {'VARIANT':<10} {'ANGLE':<25} {'STYLE':<12} {'MODE':<15} {'ASPECT':<8} {'DUR':<5}")
    print("-" * 95)
    for v in variants:
        s = v["settings"]
        print(f"{v['format']:<20} {v['variant']:<10} {v['angle']:<25} {v['style']:<12} {s['mode']:<15} {s['aspect_ratio']:<8} {s['duration']:<5}")

    return str(matrix_path)


def main():
    parser = argparse.ArgumentParser(description="Build A/B test matrix")
    parser.add_argument("--product", default=None)
    parser.add_argument("--description", default=None)
    parser.add_argument("--brand-slug", default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--selling-points", default=None)
    parser.add_argument("--audience", default=None)
    parser.add_argument("--product-slug", default=None)
    parser.add_argument("--subject-slug", default=None)
    parser.add_argument("--mood-slug", default=None)
    parser.add_argument("--lifestyle-images", default=None)

    args = parser.parse_args()
    build_matrix(args)


if __name__ == "__main__":
    main()
