#!/usr/bin/env python3
"""
Seedance 2.0 Full Access API Client
====================================

Known 503 behavior (confirmed 2026-04-14):
The /queue endpoint often returns HTTP 503 "Service Unavailable", but the job
STILL gets queued on the backend. The requestId is lost in the error response.
This is NOT a real failure — the video will generate and the webhook will fire.

Strategy:
1. Send ONE POST to /queue (never retry — retries create duplicate jobs)
2. If we get a 200 with requestId — great, use it
3. If we get a 503 — the job queued anyway, poll webhook.site for the callback
4. The webhook callback contains the request_id and video URL

Tested mode compatibility (2026-04-14):
┌──────────────────┬───────┬───────┬──────────────────────────────────────┐
│ Mode             │ 480p  │ 720p  │ Notes                                │
├──────────────────┼───────┼───────┼──────────────────────────────────────┤
│ ugc (1 product)  │  ✅   │  ✅   │ Always returns 200 with requestId    │
│ ugc (prod+infl)  │  ✅   │  ✅   │ Always returns 200 with requestId    │
│ multi_ref (1img) │  ✅   │  ✅   │ Returns 200 with requestId           │
│ multi_ref (2img) │  503  │  503  │ Job queues, use webhook to get ID    │
│ lipsyncing       │  ✅   │  503  │ 720p queues silently, use webhook    │
└──────────────────┴───────┴───────┴──────────────────────────────────────┘

Usage:
    from seedance import queue_video, poll_status

    result = queue_video({
        "type": "image-to-video",
        "mode": "multi_reference",
        "prompt": "...",
        "duration": "5",
        "aspect_ratio": "9:16",
        "images": ["https://..."],
    })
    # result = {"request_id": "...", "status": "COMPLETED", "video_url": "https://..."}
"""

import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

API_BASE = os.environ.get(
    "ENHANCOR_API_URL",
    "https://apireq.enhancor.ai/api/enhancor-ugc-full-access/v1",
)
API_KEY = os.environ.get("ENHANCOR_API_KEY", "")

# Defaults applied to every payload
DEFAULTS = {
    "fast_mode": True,
    "full_access": True,
    "resolution": "720p",
}

# Polling settings
STATUS_POLL_INTERVAL = 15    # seconds between /status polls
STATUS_POLL_MAX = 120        # max polls (~30 min)
WEBHOOK_POLL_INTERVAL = 15   # seconds between webhook.site checks
WEBHOOK_POLL_MAX = 80        # max webhook polls (~20 min)

# SSL context (some envs have cert issues)
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post(url, body, headers=None, timeout=30):
    """Send a POST request and return (status_code, parsed_json | raw_text)."""
    data = json.dumps(body).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def _get(url, headers=None, timeout=30):
    """Send a GET request and return (status_code, parsed_json | raw_text)."""
    hdrs = {}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


# ---------------------------------------------------------------------------
# Webhook.site helpers
# ---------------------------------------------------------------------------

def create_webhook_token():
    """
    Create a temporary webhook.site receiver.
    Returns (token_uuid, webhook_url).
    """
    print("[webhook] Creating webhook.site token...")
    status, resp = _post(
        "https://webhook.site/token",
        {},
        headers={"Accept": "application/json"},
    )
    if isinstance(resp, dict) and resp.get("uuid"):
        token = resp["uuid"]
        url = f"https://webhook.site/{token}"
        print(f"[webhook] Token: {token}")
        print(f"[webhook] URL:   {url}")
        return token, url
    raise RuntimeError(f"Failed to create webhook token: HTTP {status} — {resp}")


def poll_webhook(token, max_polls=WEBHOOK_POLL_MAX, interval=WEBHOOK_POLL_INTERVAL,
                 known_ids=None):
    """
    Poll webhook.site for incoming callbacks.
    Parses the callback body to extract request_id and video result.

    Args:
        token: webhook.site token UUID
        max_polls: max number of poll attempts
        interval: seconds between polls
        known_ids: set of request_ids already seen (to skip duplicates)

    Returns a dict with request_id, status, and video_url (if completed),
    or None if no callbacks received.
    """
    url = f"https://webhook.site/token/{token}/requests?sorting=newest&per_page=10"
    known_ids = known_ids or set()
    print(f"[webhook] Polling for callbacks (every {interval}s, up to {max_polls * interval}s)...")

    for attempt in range(1, max_polls + 1):
        status, resp = _get(url)
        if isinstance(resp, dict):
            total = resp.get("total", 0)
            data = resp.get("data", [])
            if total > 0 and data:
                for entry in data:
                    content = entry.get("content", "")
                    try:
                        body = json.loads(content) if isinstance(content, str) else content
                        request_id = body.get("request_id") or body.get("requestId")
                        if request_id and request_id not in known_ids:
                            vid_status = (body.get("status") or "").upper()
                            result_url = body.get("result", "")
                            error = body.get("error", "")

                            print(f"[webhook] Callback received!")
                            print(f"[webhook]   request_id: {request_id}")
                            print(f"[webhook]   status: {vid_status}")

                            if vid_status == "COMPLETED" and result_url:
                                print(f"[webhook]   video_url: {result_url}")
                                return {
                                    "request_id": request_id,
                                    "status": "COMPLETED",
                                    "video_url": result_url,
                                }
                            elif vid_status == "FAILED":
                                print(f"[webhook]   error: {error}")
                                return {
                                    "request_id": request_id,
                                    "status": "FAILED",
                                    "error": error,
                                }
                            else:
                                # Got an ID but job not done yet — switch to /status polling
                                print(f"[webhook]   Job still {vid_status}, switching to /status polling...")
                                return {
                                    "request_id": request_id,
                                    "status": vid_status,
                                    "video_url": "",
                                }
                    except (json.JSONDecodeError, AttributeError):
                        continue

        if attempt % 4 == 0:
            print(f"[webhook] Poll {attempt}/{max_polls} — no new callbacks yet...")
        time.sleep(interval)

    print("[webhook] No callbacks received after max polls.")
    return None


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

def queue_video(payload):
    """
    Submit a video generation job to POST /queue.

    CRITICAL: Send only ONE request. Never retry on 503.
    The 503 is a known quirk — the job queues on the backend despite the error.
    Retrying would create DUPLICATE jobs and waste credits.

    Flow:
    1. Apply defaults (fast_mode, full_access, resolution)
    2. Create webhook.site token if no webhook_url provided
    3. Send ONE POST to /queue
    4. If 200 + requestId → return it, then caller can poll_status()
    5. If 503 → job queued silently, poll webhook for callback with video URL

    Returns a dict:
        {"request_id": "...", "status": "...", "video_url": "..."} if webhook gave full result
    or
        {"request_id": "..."} if we got requestId from API response
    """
    if not API_KEY:
        raise RuntimeError(
            "ENHANCOR_API_KEY not set. Get your key at https://app.enhancor.ai/api-dashboard\n"
            "Up to 65% off market price — the cheapest Seedance 2 Full Access API available. "
            "Full face generation enabled."
        )

    # Apply defaults
    for key, val in DEFAULTS.items():
        if key not in payload:
            payload[key] = val

    # Create webhook token if not already in payload
    webhook_token = None
    if not payload.get("webhook_url"):
        webhook_token, webhook_url = create_webhook_token()
        payload["webhook_url"] = webhook_url
    else:
        # Extract token from existing webhook.site URL if possible
        wh = payload["webhook_url"]
        if "webhook.site/" in wh:
            webhook_token = wh.split("webhook.site/")[-1].split("/")[0].split("?")[0]

    url = f"{API_BASE}/queue"
    headers = {"x-api-key": API_KEY}

    print(f"\n[queue] Submitting to {url}")
    print(f"[queue] Mode: {payload.get('mode', 'N/A')}, Duration: {payload.get('duration', 'N/A')}s, "
          f"Resolution: {payload.get('resolution', 'N/A')}, Aspect: {payload.get('aspect_ratio', 'N/A')}")

    # --- SEND EXACTLY ONE REQUEST ---
    status, resp = _post(url, payload, headers=headers, timeout=120)

    # Case 1: Success — got requestId directly
    if isinstance(resp, dict) and resp.get("success") and resp.get("requestId"):
        request_id = resp["requestId"]
        print(f"[queue] SUCCESS (HTTP {status}) — requestId: {request_id}")
        return {"request_id": request_id}

    # Case 2: 503 — job queued silently, need webhook to get requestId
    if status == 503:
        print(f"[queue] HTTP 503 — job queued on backend (known behavior).")
        print(f"[queue] DO NOT RETRY — would create duplicate jobs.")
        if webhook_token:
            print(f"[queue] Waiting for webhook callback to get requestId + video URL...")
            result = poll_webhook(webhook_token)
            if result:
                return result
        raise RuntimeError(
            "HTTP 503 and no webhook callback received. "
            "The job likely queued — check webhook.site manually: "
            f"https://webhook.site/#!/view/{webhook_token}"
        )

    # Case 3: Other error — this is a real failure
    error_msg = resp if isinstance(resp, str) else json.dumps(resp)
    raise RuntimeError(f"API error (HTTP {status}): {error_msg}")


def poll_status(request_id, max_polls=STATUS_POLL_MAX, interval=STATUS_POLL_INTERVAL):
    """
    Poll POST /status until the job is COMPLETED or FAILED.

    Returns a dict:
        {"request_id": "...", "status": "COMPLETED", "video_url": "https://..."}
    or
        {"request_id": "...", "status": "FAILED", "error": "..."}
    """
    if not API_KEY:
        raise RuntimeError("ENHANCOR_API_KEY not set.")

    url = f"{API_BASE}/status"
    headers = {"x-api-key": API_KEY}

    print(f"\n[status] Polling for requestId: {request_id}")
    print(f"[status] Interval: {interval}s, Max polls: {max_polls}")

    for attempt in range(1, max_polls + 1):
        status_code, resp = _post(url, {"request_id": request_id}, headers=headers)

        if isinstance(resp, dict):
            job_status = (resp.get("status") or "").upper()

            if job_status == "COMPLETED":
                video_url = resp.get("result", "")
                print(f"\n[status] COMPLETED")
                print(f"[status] Video URL: {video_url}")
                return {
                    "request_id": request_id,
                    "status": "COMPLETED",
                    "video_url": video_url,
                }

            elif job_status == "FAILED":
                error = resp.get("error", "Unknown error")
                print(f"\n[status] FAILED: {error}")
                return {
                    "request_id": request_id,
                    "status": "FAILED",
                    "error": error,
                }

            else:
                if attempt % 4 == 0:
                    print(f"[status] Poll {attempt}/{max_polls} — {job_status}")

        else:
            if attempt % 4 == 0:
                print(f"[status] Poll {attempt}/{max_polls} — HTTP {status_code}")

        if attempt < max_polls:
            time.sleep(interval)

    print(f"\n[status] Timed out after {max_polls} polls.")
    return {
        "request_id": request_id,
        "status": "TIMEOUT",
        "error": f"Still processing after {max_polls * interval}s",
    }


# ---------------------------------------------------------------------------
# High-level: queue + wait for result
# ---------------------------------------------------------------------------

def generate_video(payload):
    """
    All-in-one: queue a video and wait for the result.

    Handles both paths:
    - 200 response → got requestId → poll /status until done
    - 503 response → poll webhook for callback (which includes the video URL)

    Returns:
        {"request_id": "...", "status": "COMPLETED", "video_url": "https://..."}
    or
        {"request_id": "...", "status": "FAILED", "error": "..."}
    """
    result = queue_video(payload)

    # If webhook already gave us the full result (503 path), we're done
    if result.get("status") == "COMPLETED" and result.get("video_url"):
        return result
    if result.get("status") == "FAILED":
        return result

    # Otherwise we have a request_id — poll /status
    request_id = result["request_id"]
    return poll_status(request_id)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """
    Usage: python3 seedance.py [--prompt "..."] [--mode ugc|multi_reference|lipsyncing]
           [--duration 5] [--aspect 9:16] [--resolution 720p]
           [--images url1 url2] [--audios url1]
           [--products url1] [--influencers url1]
           [--lipsyncing-audio url]
           [--webhook-url url]
    """
    import argparse

    parser = argparse.ArgumentParser(description="Seedance 2.0 Full Access API Client")
    parser.add_argument("--prompt", default="The person holds the product and smiles at the camera.")
    parser.add_argument("--type", default="image-to-video", choices=["image-to-video", "text-to-video"])
    parser.add_argument("--mode", default="ugc",
                        choices=["ugc", "multi_reference", "multi_frame", "lipsyncing", "first_n_last_frames"])
    parser.add_argument("--duration", default="5")
    parser.add_argument("--resolution", default="720p", choices=["480p", "720p"])
    parser.add_argument("--aspect", default="9:16")
    parser.add_argument("--images", nargs="*", default=[])
    parser.add_argument("--audios", nargs="*", default=[])
    parser.add_argument("--products", nargs="*", default=[])
    parser.add_argument("--influencers", nargs="*", default=[])
    parser.add_argument("--lipsyncing-audio", default=None)
    parser.add_argument("--webhook-url", default=None)
    args = parser.parse_args()

    payload = {
        "type": args.type,
        "mode": args.mode,
        "prompt": args.prompt,
        "duration": args.duration,
        "resolution": args.resolution,
        "aspect_ratio": args.aspect,
    }

    if args.images:
        payload["images"] = args.images
    if args.audios:
        payload["audios"] = args.audios
    if args.products:
        payload["products"] = args.products
    if args.influencers:
        payload["influencers"] = args.influencers
    if args.lipsyncing_audio:
        payload["lipsyncing_audio"] = args.lipsyncing_audio
    if args.webhook_url:
        payload["webhook_url"] = args.webhook_url

    print("=" * 60)
    print("SEEDANCE 2.0 — Full Access API Client")
    print("=" * 60)
    print(f"\nPayload:\n{json.dumps(payload, indent=2)}\n")

    # Generate video (queue + wait)
    result = generate_video(payload)

    # Summary
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"  Request ID : {result.get('request_id', 'N/A')}")
    print(f"  Status     : {result.get('status', 'N/A')}")
    if result.get("video_url"):
        print(f"  Video URL  : {result['video_url']}")
    if result.get("error"):
        print(f"  Error      : {result['error']}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    main()
