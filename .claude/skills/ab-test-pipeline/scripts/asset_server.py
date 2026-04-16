#!/usr/bin/env python3
"""
Asset Wizard — Local Web Server
Pure Python HTTP server for the drag-and-drop asset upload UI.

Endpoints:
  GET  /                  → Serves app/index.html
  GET  /app/*             → Serves static UI files
  GET  /assets/*          → Serves asset images for preview
  GET  /api/registry      → Returns assets/registry.json
  POST /api/upload        → Receives image + metadata, sorts into library
  POST /api/context       → Saves AI context (called by Claude CLI)
  POST /api/delete        → Removes an asset from the library
"""

import cgi
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[4] / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parents[4]
ASSETS_DIR = BASE_DIR / "assets"
REGISTRY_PATH = ASSETS_DIR / "registry.json"
BACKUPS_DIR = ASSETS_DIR / "backups"
APP_DIR = BASE_DIR / "app"
INBOX_DIR = ASSETS_DIR / "inbox"
PROJECTS_DIR = BASE_DIR / "projects"
BRANDS_PATH = BASE_DIR / "config" / "brands.json"

PORT = 8092

CATEGORY_DIRS = {"product": "products", "subject": "subjects", "mood": "moods", "audio": "audio"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def get_image_dimensions(filepath):
    try:
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(filepath)],
            capture_output=True, text=True, timeout=5,
        )
        w = h = "?"
        for line in result.stdout.splitlines():
            if "pixelWidth" in line:
                w = line.split(":")[-1].strip()
            if "pixelHeight" in line:
                h = line.split(":")[-1].strip()
        return f"{w}x{h}"
    except Exception:
        return "unknown"


def load_registry():
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {"version": 1, "updated_at": None, "products": {}, "subjects": {}, "moods": {}, "audio": {}}


def save_registry(registry):
    registry["updated_at"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def get_next_number(target_dir, slug, asset_type):
    existing = list(target_dir.glob(f"{slug}-{asset_type}-*"))
    numbers = []
    for f in existing:
        parts = f.stem.rsplit("-", 1)
        if len(parts) == 2:
            try:
                numbers.append(int(parts[1]))
            except ValueError:
                pass
    return max(numbers, default=0) + 1


def sort_asset(source_path, asset_type, slug, name, description=""):
    """Sort a single asset into the library and update registry."""
    source = Path(source_path)
    if not source.exists():
        return {"error": f"File not found: {source}"}

    slug = slug.lower().strip().replace(" ", "-").replace("_", "-")
    category_dir = CATEGORY_DIRS.get(asset_type)
    if not category_dir:
        return {"error": f"Invalid type: {asset_type}"}

    target_dir = ASSETS_DIR / category_dir / slug
    target_dir.mkdir(parents=True, exist_ok=True)

    next_num = get_next_number(target_dir, slug, asset_type)
    ext = source.suffix.lower()
    new_filename = f"{slug}-{asset_type}-{next_num:02d}{ext}"
    target_path = target_dir / new_filename

    is_audio = source.suffix.lower() in AUDIO_EXTENSIONS
    dims = "audio" if is_audio else get_image_dimensions(source)
    original_name = source.name

    # Backup original
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

    shutil.move(str(source), str(target_path))

    registry = load_registry()
    # Ensure category key exists in registry
    if category_dir not in registry:
        registry[category_dir] = {}

    items_key = "audio" if is_audio else "images"

    if slug not in registry[category_dir]:
        registry[category_dir][slug] = {"name": name, "description": description, items_key: []}
    elif description and not registry[category_dir][slug].get("description"):
        registry[category_dir][slug]["description"] = description

    # Ensure the items list exists
    if items_key not in registry[category_dir][slug]:
        registry[category_dir][slug][items_key] = []

    rel_path = str(target_path.relative_to(BASE_DIR))

    entry = {
        "path": rel_path,
        "original_name": original_name,
        "added_at": datetime.now().isoformat(),
        "ai_context": None,
    }
    if is_audio:
        entry["file_size_mb"] = round(target_path.stat().st_size / (1024 * 1024), 2) if target_path.exists() else 0
    else:
        entry["dimensions"] = dims

    registry[category_dir][slug][items_key].append(entry)
    save_registry(registry)

    return {
        "success": True,
        "slug": slug,
        "name": name,
        "type": asset_type,
        "category": category_dir,
        "new_path": rel_path,
        "dimensions": dims,
        "original_name": original_name,
    }


class AssetHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, filepath):
        if not filepath.exists():
            self.send_error(404, "Not found")
            return
        mime, _ = mimetypes.guess_type(str(filepath))
        # Ensure audio MIME types are correct
        audio_mimes = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
                       ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac"}
        ext = filepath.suffix.lower()
        if ext in audio_mimes:
            mime = audio_mimes[ext]
        mime = mime or "application/octet-stream"
        data = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_video(self, filepath):
        """Serve video files with range request support for streaming."""
        if not filepath.exists():
            self.send_error(404, "Not found")
            return
        mime, _ = mimetypes.guess_type(str(filepath))
        mime = mime or "video/mp4"
        stat = filepath.stat()
        size = stat.st_size

        range_header = self.headers.get("Range")
        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else size - 1
            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", length)
            self.send_header("Content-Type", mime)
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(filepath, "rb") as f:
                f.seek(start)
                self.wfile.write(f.read(length))
        else:
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", size)
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(filepath, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

    def do_GET(self):
        path = unquote(self.path.split("?")[0])

        if path == "/" or path == "/index.html":
            self.send_file(APP_DIR / "index.html")
        elif path.startswith("/app/"):
            self.send_file(APP_DIR / path[5:])
        elif path.startswith("/assets/"):
            self.send_file(ASSETS_DIR / path[8:])
        elif path.startswith("/projects/"):
            # Serve project files (videos, reports, matrix)
            fpath = PROJECTS_DIR / path[10:]
            if fpath.suffix.lower() in (".mp4", ".webm", ".mov"):
                self.send_video(fpath)
            else:
                self.send_file(fpath)
        elif path == "/api/registry":
            self.send_json(load_registry())
        elif path == "/api/brands":
            if BRANDS_PATH.exists():
                with open(BRANDS_PATH) as f:
                    self.send_json(json.load(f))
            else:
                self.send_json({"version": 1, "brands": {}})
        elif path == "/api/outputs":
            self.send_json(self.get_outputs())
        elif path == "/api/inbox":
            images = []
            if INBOX_DIR.exists():
                for f in sorted(INBOX_DIR.iterdir()):
                    if f.is_file() and f.suffix.lower() in (IMAGE_EXTENSIONS | AUDIO_EXTENSIONS):
                        images.append({
                            "filename": f.name,
                            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                            "dimensions": get_image_dimensions(f),
                        })
            self.send_json(images)
        else:
            self.send_error(404, "Not found")

    def get_outputs(self):
        """Scan projects/ for generated videos, grouped by product."""
        outputs = {}
        if not PROJECTS_DIR.exists():
            return outputs
        for project_dir in sorted(PROJECTS_DIR.iterdir(), reverse=True):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            matrix_path = project_dir / "matrix.json"
            if not matrix_path.exists():
                continue
            try:
                with open(matrix_path) as f:
                    matrix = json.load(f)
            except Exception:
                continue

            product = matrix.get("project", {}).get("product", "Unknown")
            product_slug = product.lower().replace(" ", "-")
            created = matrix.get("project", {}).get("created_at", "")

            videos = []
            for v in matrix.get("variants", []):
                video_file = project_dir / v.get("output_file", "")
                videos.append({
                    "id": v.get("id", ""),
                    "format": v.get("format", ""),
                    "variant": v.get("variant", 0),
                    "angle": v.get("angle", ""),
                    "status": v.get("status", "pending"),
                    "settings": v.get("settings", {}),
                    "has_video": video_file.exists(),
                    "video_path": f"projects/{project_dir.name}/{v.get('output_file', '')}" if video_file.exists() else None,
                    "video_size_mb": round(video_file.stat().st_size / 1048576, 1) if video_file.exists() else 0,
                })

            run = {
                "project_dir": project_dir.name,
                "product": product,
                "product_slug": product_slug,
                "created_at": created,
                "total_variants": matrix.get("total_variants", 0),
                "completed": sum(1 for v in videos if v["has_video"]),
                "videos": videos,
                "has_report": (project_dir / "report.html").exists(),
                "report_path": f"projects/{project_dir.name}/report.html" if (project_dir / "report.html").exists() else None,
            }

            if product_slug not in outputs:
                outputs[product_slug] = {"product": product, "runs": []}
            outputs[product_slug]["runs"].append(run)

        return outputs

    def do_POST(self):
        path = unquote(self.path.split("?")[0])

        if path == "/api/upload":
            self.handle_upload()
        elif path == "/api/context":
            self.handle_context()
        elif path == "/api/delete":
            self.handle_delete()
        elif path == "/api/webhook":
            self.handle_webhook()
        else:
            self.send_error(404, "Not found")

    def handle_upload(self):
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
            )

            file_item = form["file"]
            category = form.getfirst("category", "product")
            slug = form.getfirst("slug", "unnamed")
            name = form.getfirst("name", slug.title())
            description = form.getfirst("description", "")

            if not file_item.filename:
                self.send_json({"error": "No file uploaded"}, 400)
                return

            INBOX_DIR.mkdir(parents=True, exist_ok=True)
            inbox_path = INBOX_DIR / file_item.filename
            with open(inbox_path, "wb") as f:
                f.write(file_item.file.read())

            result = sort_asset(str(inbox_path), category, slug, name, description)
            self.send_json(result)

        elif "application/json" in content_type:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            result = sort_asset(
                str(BASE_DIR / body["file"]),
                body["category"],
                body["slug"],
                body.get("name", body["slug"].title()),
                body.get("description", ""),
            )
            self.send_json(result)
        else:
            self.send_json({"error": "Unsupported content type"}, 400)

    def handle_context(self):
        """Save AI context for an image. Called by Claude CLI after vision analysis."""
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        image_path = body.get("path")
        ai_context = body.get("ai_context")

        if not image_path or not ai_context:
            self.send_json({"error": "Missing path or ai_context"}, 400)
            return

        registry = load_registry()
        updated = False
        for cat in ["products", "subjects", "moods", "audio"]:
            for slug, data in registry.get(cat, {}).items():
                items = data.get("images", []) + data.get("audio", [])
                for img in items:
                    if img["path"] == image_path:
                        img["ai_context"] = ai_context
                        updated = True
                        break

        if updated:
            save_registry(registry)
            self.send_json({"success": True})
        else:
            self.send_json({"error": f"Image path not found: {image_path}"}, 404)

    def handle_delete(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        category = body.get("category")
        slug = body.get("slug")
        image_path = body.get("path")

        if not all([category, slug]):
            self.send_json({"error": "Missing category or slug"}, 400)
            return

        registry = load_registry()
        cat_key = CATEGORY_DIRS.get(category, category)

        if slug not in registry.get(cat_key, {}):
            self.send_json({"error": f"Slug '{slug}' not found"}, 404)
            return

        slug_dir = ASSETS_DIR / cat_key / slug

        if image_path:
            full_path = BASE_DIR / image_path
            if full_path.exists():
                full_path.unlink()
            registry[cat_key][slug]["images"] = [
                img for img in registry[cat_key][slug]["images"]
                if img["path"] != image_path
            ]
            if not registry[cat_key][slug]["images"]:
                del registry[cat_key][slug]
                if slug_dir.exists() and not any(slug_dir.iterdir()):
                    slug_dir.rmdir()
        else:
            for img in registry[cat_key][slug].get("images", []):
                fp = BASE_DIR / img["path"]
                if fp.exists():
                    fp.unlink()
            del registry[cat_key][slug]
            if slug_dir.exists():
                shutil.rmtree(str(slug_dir), ignore_errors=True)

        save_registry(registry)
        self.send_json({"success": True})

    def handle_webhook(self):
        """
        Webhook endpoint for Enhancor API callbacks.
        When a video generation completes, Enhancor POSTs here with the result.
        This updates matrix.json and downloads the video automatically.
        """
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        request_id = body.get("requestId") or body.get("request_id") or ""
        status = (body.get("status") or "").upper()
        video_url = body.get("result") or body.get("video_url") or ""
        cost = body.get("cost", 0)

        print(f"  [WEBHOOK] requestId={request_id} status={status} cost={cost}")

        if not request_id:
            self.send_json({"error": "Missing requestId"}, 400)
            return

        # Log the raw webhook payload
        webhook_log = PROJECTS_DIR / "webhook_log.jsonl"
        try:
            with open(webhook_log, "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "payload": body,
                }) + "\n")
        except Exception:
            pass

        # Find which project/variant this belongs to and update matrix.json
        updated = False
        for project_dir in sorted(PROJECTS_DIR.iterdir(), reverse=True):
            if not project_dir.is_dir():
                continue
            matrix_path = project_dir / "matrix.json"
            if not matrix_path.exists():
                continue
            try:
                with open(matrix_path) as f:
                    matrix = json.load(f)
            except Exception:
                continue

            for v in matrix.get("variants", []):
                gen_id = v.get("generation_id") or v.get("request_id") or ""
                if gen_id == request_id:
                    # Match found — update this variant
                    if status == "COMPLETED" and video_url:
                        v["status"] = "completed"
                        v["video_url"] = video_url
                        v["cost"] = cost

                        # Download the video
                        out_path = project_dir / v.get("output_file", f"{v['id']}.mp4")
                        try:
                            import urllib.request as urlreq
                            urlreq.urlretrieve(video_url, str(out_path))
                            size_mb = out_path.stat().st_size / 1048576
                            print(f"  [WEBHOOK] Downloaded {out_path.name} ({size_mb:.1f} MB)")
                        except Exception as e:
                            print(f"  [WEBHOOK] Download failed: {e}")
                            v["status"] = "download_failed"

                    elif status == "FAILED":
                        v["status"] = "error"
                        v["error"] = body.get("error", "Generation failed")

                    # Save the API response to jsonl log
                    log_path = project_dir / "api_responses.jsonl"
                    try:
                        with open(log_path, "a") as f:
                            f.write(json.dumps({
                                "timestamp": datetime.now().isoformat(),
                                "source": "webhook",
                                "request_id": request_id,
                                "response": body,
                            }) + "\n")
                    except Exception:
                        pass

                    # Save updated matrix
                    with open(matrix_path, "w") as f:
                        json.dump(matrix, f, indent=2)
                    updated = True
                    print(f"  [WEBHOOK] Updated {project_dir.name}/{v['id']} -> {v['status']}")
                    break
            if updated:
                break

        if updated:
            self.send_json({"success": True, "request_id": request_id})
        else:
            print(f"  [WEBHOOK] No matching variant for requestId={request_id}")
            self.send_json({"warning": "No matching variant found", "request_id": request_id})


def main():
    server = HTTPServer(("localhost", PORT), AssetHandler)
    print(f"Asset Wizard UI running at http://localhost:{PORT}")
    print(f"Serving from: {BASE_DIR}")
    print(f"Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
