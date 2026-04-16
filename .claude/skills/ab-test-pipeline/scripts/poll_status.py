#!/usr/bin/env python3
"""
Enhancor Seedance 2 Full Access API — Status Poller
Polls generation status and downloads completed videos.

Checks matrix.json first for externally updated statuses (e.g. from webhooks)
before hitting the API. Uses staggered requests with backoff to avoid rate limits.

API Reference:
  Base URL: https://apireq.enhancor.ai/api/enhancor-ugc-full-access/v1
  Status: POST /status with {"request_id": "..."}
  Statuses: PENDING, IN_QUEUE, IN_PROGRESS, COMPLETED, FAILED
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[4] / ".env")
except ImportError:
    pass

ENHANCOR_API_URL = os.environ.get("ENHANCOR_API_URL", "https://apireq.enhancor.ai/api/enhancor-ugc-full-access/v1")
ENHANCOR_API_KEY = os.environ.get("ENHANCOR_API_KEY", "")

POLL_INTERVAL = 120  # seconds between full rounds (2 minutes)
PER_REQUEST_DELAY = 5  # seconds between individual API calls within a round
MAX_POLLS = 60  # 60 rounds * 2 min = 2 hours max
RETRY_BACKOFF = 60  # seconds to wait after a 429 rate limit error


def log_api_response(request_id, response):
    """Append raw API JSON response to a log file in the project directory for debugging."""
    try:
        # Find the project dir from the matrix path (set during run())
        if not hasattr(log_api_response, "log_path"):
            return
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request_id": request_id,
            "response": response,
        }
        with open(log_api_response.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Don't let logging errors break polling


def check_status(request_id):
    """Check generation status via Enhancor POST /status."""
    url = f"{ENHANCOR_API_URL}/status"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ENHANCOR_API_KEY,
    }
    payload = json.dumps({"request_id": request_id}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            # Log raw JSON response to api_responses.jsonl for debugging
            log_api_response(request_id, result)
            return result
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return {"status": "RATE_LIMITED", "error": "429 Too Many Requests"}
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        return {"status": "ERROR", "error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def download_video(video_url, output_path):
    """Download completed video from CDN URL."""
    try:
        urllib.request.urlretrieve(video_url, output_path)
        return True
    except Exception as e:
        print(f"    Download error: {e}")
        return False


def reload_matrix(matrix_path):
    """Re-read matrix.json to pick up external updates (webhooks, manual edits)."""
    with open(matrix_path) as f:
        return json.load(f)


def run(matrix_path):
    """Poll all submitted variants until complete."""
    matrix = reload_matrix(matrix_path)

    project_dir = Path(matrix["project_dir"])

    # Set up JSON response logging in the project directory
    log_api_response.log_path = str(project_dir / "api_responses.jsonl")
    print(f"API responses logged to: {log_api_response.log_path}\n")

    active_ids = [v["id"] for v in matrix["variants"] if v["status"] == "submitted"]

    if not active_ids:
        print("No submitted variants to poll.")
        if any(v["status"] == "dry_run" for v in matrix["variants"]):
            print("Set ENHANCOR_API_KEY and run generate.py first.")
        return

    print(f"Polling {len(active_ids)} variants (every {POLL_INTERVAL}s, max {MAX_POLLS} rounds)")
    print(f"Per-request delay: {PER_REQUEST_DELAY}s to avoid rate limits\n")

    poll_count = 0
    while active_ids and poll_count < MAX_POLLS:
        poll_count += 1

        # Re-read matrix.json each round to catch external updates (webhooks, manual)
        matrix = reload_matrix(matrix_path)
        variants_by_id = {v["id"]: v for v in matrix["variants"]}

        # Check for variants already completed externally
        newly_done = []
        for vid in list(active_ids):
            v = variants_by_id[vid]
            if v["status"] == "completed" and v.get("video_url"):
                # Already completed (webhook or manual update) — just download if needed
                out = project_dir / v["output_file"]
                if not out.exists():
                    print(f"  [DONE via matrix] {v['id']} — downloading...")
                    download_video(v["video_url"], str(out))
                    if out.exists():
                        print(f"    Saved: {out.name} ({out.stat().st_size / 1048576:.1f} MB)")
                else:
                    print(f"  [DONE via matrix] {v['id']} — already downloaded")
                newly_done.append(vid)

        for vid in newly_done:
            active_ids.remove(vid)

        if not active_ids:
            break

        # Poll remaining variants via API with staggered requests
        rate_limited = False
        done_this_round = []

        for vid in list(active_ids):
            v = variants_by_id[vid]

            result = check_status(v["generation_id"])
            status = result.get("status", "UNKNOWN").upper()

            if status == "RATE_LIMITED":
                print(f"  [429] Rate limited — backing off {RETRY_BACKOFF}s...")
                rate_limited = True
                break  # Stop this round, wait longer

            elif status == "COMPLETED":
                video_url = result.get("result")
                cost = result.get("cost", "?")
                out = project_dir / v["output_file"]
                print(f"  [DONE] {v['id']} — {cost} credits")

                if video_url and download_video(video_url, str(out)):
                    v["status"] = "completed"
                    v["video_url"] = video_url
                    v["cost"] = cost
                    print(f"    Saved: {out.name} ({out.stat().st_size / 1048576:.1f} MB)")
                else:
                    v["status"] = "download_failed"
                    v["video_url"] = video_url
                done_this_round.append(vid)

            elif status == "FAILED":
                v["status"] = "error"
                v["error"] = "Generation failed (credits refunded)"
                print(f"  [FAIL] {v['id']}")
                done_this_round.append(vid)

            elif status in ("PENDING", "IN_QUEUE", "IN_PROGRESS"):
                tag = {"PENDING": "WAIT", "IN_QUEUE": "QUEUE", "IN_PROGRESS": "GEN"}[status]
                print(f"  [{tag}] {v['id']} — {status}")
            else:
                print(f"  [??] {v['id']} — {status}: {result.get('error', '')}")

            time.sleep(PER_REQUEST_DELAY)

        for vid in done_this_round:
            active_ids.remove(vid)

        # Save progress
        with open(matrix_path, "w") as f:
            json.dump(matrix, f, indent=2)

        if active_ids:
            total = matrix["total_variants"]
            c = total - len(active_ids)
            wait = RETRY_BACKOFF if rate_limited else POLL_INTERVAL
            print(f"\n  {c}/{total} done, {len(active_ids)} remaining. Next poll in {wait}s...\n")
            time.sleep(wait)

    # Summary
    matrix = reload_matrix(matrix_path)
    print("\n" + "=" * 60 + "\nFINAL STATUS\n" + "=" * 60)
    total_cost = 0
    for v in matrix["variants"]:
        icon = {"completed": "OK", "error": "FAIL", "download_failed": "DL"}.get(v["status"], "??")
        cost = v.get("cost", 0)
        if isinstance(cost, (int, float)):
            total_cost += cost
        print(f"  [{icon}] {v['id']} — {v['angle']} — {v['status']}")

    print(f"\nTotal credits: {total_cost}")


def main():
    parser = argparse.ArgumentParser(description="Poll Enhancor API for status")
    parser.add_argument("--matrix", required=True, help="Path to matrix.json")
    args = parser.parse_args()
    run(args.matrix)


if __name__ == "__main__":
    main()
