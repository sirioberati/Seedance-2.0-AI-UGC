#!/usr/bin/env python3
"""
Enhancor Seedance 2 Full Access API — Video Generation
Submits all variants from a matrix.json to the Enhancor UGC Full Access API.

API Reference:
  Base URL: https://apireq.enhancor.ai/api/enhancor-ugc-full-access/v1
  Auth: x-api-key header
  Queue: POST /queue
  Docs: https://app.enhancor.ai/api-dashboard
"""

import argparse
import json
import os
import ssl
import sys
import time
from pathlib import Path

# SSL context for hosts with self-signed certs
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[4] / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parents[4]
ENHANCOR_API_URL = os.environ.get("ENHANCOR_API_URL", "https://apireq.enhancor.ai/api/enhancor-ugc-full-access/v1")
ENHANCOR_API_KEY = os.environ.get("ENHANCOR_API_KEY", "")


def upload_file_to_hosting(file_path):
    """
    Upload any local file (image or audio) to temporary hosting.
    Uses tmpfiles.org via curl (temporary hosting, no account needed).
    Returns the direct download URL.
    """
    import subprocess

    if not os.path.exists(file_path):
        print(f"    File not found: {file_path}")
        return None

    filename = os.path.basename(file_path)

    try:
        result = subprocess.run(
            ["curl", "-s", "-F", f"file=@{file_path}", "https://tmpfiles.org/api/v1/upload"],
            capture_output=True, text=True, timeout=120,
        )
        resp = json.loads(result.stdout)
        if resp.get("status") == "success":
            page_url = resp["data"]["url"]
            # tmpfiles.org/12345/file.ext -> tmpfiles.org/dl/12345/file.ext
            direct_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
            print(f"    Uploaded: {filename} -> {direct_url}")
            return direct_url
        print(f"    Upload response: {resp}")
        return None
    except Exception as e:
        print(f"    Upload error: {e}")
        return None


# Keep backward compat alias
upload_image_to_hosting = upload_file_to_hosting


def resolve_image_url(path):
    """Resolve a local path to a public URL. Pass through if already a URL."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return upload_file_to_hosting(path)


def submit_variant(variant):
    """Submit a single variant to the Enhancor Seedance 2 POST /queue endpoint."""
    import urllib.request
    import urllib.error

    if not ENHANCOR_API_KEY:
        return None

    settings = variant["settings"]
    mode = settings["mode"]

    # Map internal mode names to Enhancor API modes
    # "ugc" is a valid API mode in the Full Access API
    api_mode = {
        "ugc": "ugc",
        "multi_input": "multi_reference",
        "multi_reference": "multi_reference",
        "lipsyncing": "lipsyncing",
        "multi_frame": "multi_frame",
        "first_n_last_frames": "first_n_last_frames",
    }.get(mode, "ugc")

    # Build payload per Enhancor Full Access API spec
    payload = {
        "prompt": variant["prompt"],
        "type": "image-to-video",
        "mode": api_mode,
        "duration": str(settings["duration"]),
        "aspect_ratio": settings["aspect_ratio"],
        "full_access": True,
        "webhook_url": os.environ.get("WEBHOOK_URL") or "https://webhook.site/placeholder",
    }

    # Resolve product images
    product_paths = variant.get("images", {}).get("products", [])
    product_urls = [u for u in (resolve_image_url(p) for p in product_paths if p) if u]

    # Resolve subject/influencer images
    subject_path = variant.get("images", {}).get("subject")
    influencer_urls = []
    if subject_path:
        u = resolve_image_url(subject_path)
        if u:
            influencer_urls.append(u)

    # Resolve reference/mood images
    ref_paths = variant.get("images", {}).get("references", [])
    ref_urls = [u for u in (resolve_image_url(p) for p in ref_paths if p) if u]

    # Attach images based on mode
    if api_mode == "ugc":
        # UGC mode uses products[] and influencers[] fields
        if product_urls:
            payload["products"] = product_urls
        if influencer_urls:
            payload["influencers"] = influencer_urls
        # Additional reference images go into images[]
        if ref_urls:
            payload["images"] = ref_urls
    else:
        # multi_reference mode uses images[] for everything
        all_urls = product_urls + influencer_urls + ref_urls
        if all_urls:
            payload["images"] = all_urls

    # Resolve audio reference — Enhancor API field is "audios" (string[]), max 3
    # Ref in prompt as @audio1, @audio2, @audio3
    audio_path = variant.get("images", {}).get("audio")
    if audio_path:
        audio_url = resolve_image_url(audio_path)
        if audio_url:
            payload["audios"] = [audio_url]

    # Fallback to text-to-video if no images
    has_media = any([payload.get("products"), payload.get("influencers"), payload.get("images")])
    if not has_media:
        payload["type"] = "text-to-video"
        payload.pop("mode", None)

    # Debug: print full payload
    print(f"  [PAYLOAD] {json.dumps({k: v for k, v in payload.items() if k != 'prompt'}, indent=2)}")

    # Submit
    url = f"{ENHANCOR_API_URL}/queue"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ENHANCOR_API_KEY,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("success"):
                request_id = result.get("requestId")
                print(f"  [OK] {variant['id']} -> requestId: {request_id}")
                return request_id
            else:
                print(f"  [ERR] {variant['id']} -> {result}")
                return None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        print(f"  [ERR] {variant['id']} -> HTTP {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"  [ERR] {variant['id']} -> {e}")
        return None


def run(matrix_path):
    """Submit all variants in the matrix."""
    with open(matrix_path) as f:
        matrix = json.load(f)

    print(f"Submitting {matrix['total_variants']} variants to Enhancor Seedance 2")
    print(f"API: {ENHANCOR_API_URL}")
    print(f"Key: {'***' + ENHANCOR_API_KEY[-4:] if ENHANCOR_API_KEY else 'NOT SET'}")
    print()

    if not ENHANCOR_API_KEY:
        print("ENHANCOR_API_KEY not set.")
        print("1. Get your key: https://app.enhancor.ai/api-dashboard")
        print("2. Copy .env.example to .env and add your key")
        print()
        print("DRY RUN -- prompts saved, not submitted.\n")

        for variant in matrix["variants"]:
            variant["status"] = "dry_run"
            print(f"  [DRY] {variant['id']} -- {variant['angle']} ({variant['settings']['mode']}, {variant['settings']['aspect_ratio']})")

        with open(matrix_path, "w") as f:
            json.dump(matrix, f, indent=2)
        return

    submitted = 0
    for variant in matrix["variants"]:
        if variant["status"] not in ("pending", "dry_run"):
            print(f"  [SKIP] {variant['id']} -- {variant['status']}")
            continue

        request_id = submit_variant(variant)
        if request_id:
            variant["generation_id"] = request_id
            variant["status"] = "submitted"
            submitted += 1
        else:
            variant["status"] = "error"
            variant["error"] = "Failed to submit"

        time.sleep(2)

    with open(matrix_path, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"\nSubmitted: {submitted}/{matrix['total_variants']}")
    print(f"Matrix updated: {matrix_path}")


def main():
    parser = argparse.ArgumentParser(description="Submit variants to Enhancor Seedance 2 API")
    parser.add_argument("--matrix", required=True, help="Path to matrix.json")
    args = parser.parse_args()
    run(args.matrix)


if __name__ == "__main__":
    main()
