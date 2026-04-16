#!/usr/bin/env python3
"""
A/B Test Report Generator
Creates an HTML comparison dashboard from a completed matrix.
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


def generate_report(matrix_path):
    """Generate HTML report from matrix.json."""
    with open(matrix_path) as f:
        matrix = json.load(f)

    project = matrix["project"]
    project_dir = Path(matrix["project_dir"])
    variants = matrix["variants"]

    # Group by format
    formats = {}
    for v in variants:
        fmt = v["format"]
        if fmt not in formats:
            formats[fmt] = []
        formats[fmt].append(v)

    format_labels = {
        "podcast": "Podcast Ad",
        "ugc": "UGC Ad",
        "lifestyle": "Lifestyle Ad",
        "greenscreen": "Greenscreen TikTok",
        "Podcast Ad": "Podcast Ad",
        "UGC Ad": "UGC Ad",
        "Lifestyle Ad": "Lifestyle Ad",
        "Greenscreen TikTok": "Greenscreen TikTok",
    }

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A/B Test Report — {project['product']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #050505;
            color: #ffffff;
            padding: 40px 24px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 32px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .header .accent {{ color: #3344FF; }}
        .header .meta {{
            color: rgba(255,255,255,0.5);
            font-size: 14px;
        }}
        .stats {{
            display: flex;
            gap: 24px;
            justify-content: center;
            margin-top: 20px;
        }}
        .stat {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 16px 24px;
            text-align: center;
        }}
        .stat-value {{ font-size: 24px; font-weight: 700; color: #3344FF; }}
        .stat-label {{ font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 4px; }}
        .format-section {{
            margin-bottom: 48px;
        }}
        .format-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            padding-left: 16px;
            border-left: 3px solid #3344FF;
        }}
        .format-meta {{
            display: inline-flex;
            gap: 12px;
            margin-left: 16px;
            font-size: 12px;
            color: rgba(255,255,255,0.4);
        }}
        .format-meta span {{
            background: rgba(255,255,255,0.05);
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .variants-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        .variant-card {{
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            overflow: hidden;
            transition: border-color 0.2s;
        }}
        .variant-card:hover {{
            border-color: rgba(51,68,255,0.3);
        }}
        .variant-header {{
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .variant-label {{
            font-weight: 600;
            font-size: 14px;
        }}
        .variant-angle {{
            font-size: 12px;
            color: #3344FF;
            background: rgba(51,68,255,0.1);
            padding: 4px 10px;
            border-radius: 20px;
        }}
        .variant-style {{
            font-size: 11px;
            color: rgba(255,255,255,0.4);
            background: rgba(255,255,255,0.05);
            padding: 3px 8px;
            border-radius: 4px;
            margin-left: 8px;
        }}
        .video-container {{
            aspect-ratio: 16/9;
            background: #111;
            position: relative;
        }}
        .video-container.vertical {{
            aspect-ratio: 9/16;
            max-height: 500px;
        }}
        .video-container video {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}
        .no-video {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: rgba(255,255,255,0.3);
            font-size: 14px;
        }}
        .status-badge {{
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 500;
        }}
        .status-completed {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
        .status-pending {{ background: rgba(234,179,8,0.15); color: #eab308; }}
        .status-error {{ background: rgba(239,68,68,0.15); color: #ef4444; }}
        .status-dry_run {{ background: rgba(139,92,246,0.15); color: #8b5cf6; }}
        .prompt-section {{
            padding: 16px 20px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }}
        .prompt-toggle {{
            font-size: 12px;
            color: rgba(255,255,255,0.5);
            cursor: pointer;
            user-select: none;
        }}
        .prompt-toggle:hover {{ color: #3344FF; }}
        .prompt-text {{
            display: block;
            margin-top: 12px;
            font-size: 13px;
            line-height: 1.6;
            color: rgba(255,255,255,0.6);
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
            padding: 12px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
        }}
        .prompt-text.visible {{ display: block; }}
        .footer {{
            text-align: center;
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid rgba(255,255,255,0.1);
            color: rgba(255,255,255,0.3);
            font-size: 12px;
        }}
        @media (max-width: 768px) {{
            .variants-grid {{ grid-template-columns: 1fr; }}
            .stats {{ flex-wrap: wrap; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>A/B Test Report — <span class="accent">{project['product']}</span></h1>
            <p class="meta">{project['description']} | {project.get('created_at', '')[:10]}</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{matrix['total_variants']}</div>
                    <div class="stat-label">Total Variants</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(formats)}</div>
                    <div class="stat-label">Ad Formats</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{sum(1 for v in variants if v['status'] == 'completed')}</div>
                    <div class="stat-label">Completed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{project.get('audience', 'N/A')[:30]}</div>
                    <div class="stat-label">Target Audience</div>
                </div>
            </div>
        </div>
"""

    # Try both short keys and full names
    ordered_keys = ["podcast", "ugc", "lifestyle", "greenscreen",
                    "Podcast Ad", "UGC Ad", "Lifestyle Ad", "Greenscreen TikTok"]
    for fmt_key in ordered_keys:
        if fmt_key not in formats:
            continue
        fmt_variants = formats[fmt_key]
        fmt_settings = fmt_variants[0]["settings"]
        is_vertical = fmt_settings["aspect_ratio"] == "9:16"
        label = format_labels.get(fmt_key, fmt_key.title())

        html += f"""
        <div class="format-section">
            <h2 class="format-title">{label}
                <span class="format-meta">
                    <span>{fmt_settings['mode']}</span>
                    <span>{fmt_settings['aspect_ratio']}</span>
                    <span>{fmt_settings['duration']}s</span>
                </span>
            </h2>
            <div class="variants-grid">
"""

        for v in fmt_variants:
            status_class = f"status-{v['status'].replace(' ', '_')}"
            video_file = v["output_file"]
            video_exists = (project_dir / video_file).exists()
            container_class = "video-container vertical" if is_vertical else "video-container"
            prompt_id = v["id"].replace("-", "_")

            html += f"""
                <div class="variant-card">
                    <div class="variant-header">
                        <div>
                            <span class="variant-label">{v['id']}</span>
                            <span class="variant-style">{v.get('style', v.get('angle', ''))}</span>
                        </div>
                        <div>
                            <span class="variant-angle">{v['angle']}</span>
                            <span class="status-badge {status_class}">{v['status']}</span>
                        </div>
                    </div>
                    <div class="{container_class}">
"""
            if video_exists:
                html += f"""                        <video controls preload="auto" playsinline muted src="{video_file}#t=0.5" onplay="this.muted=false">
                        </video>
"""
            else:
                html += f"""                        <div class="no-video">Video {v['status']}</div>
"""

            # Escape prompt for HTML
            escaped_prompt = (
                v["prompt"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

            html += f"""                    </div>
                    <div class="prompt-section">
                        <div class="prompt-toggle" onclick="togglePrompt('{prompt_id}')">Hide prompt</div>
                        <div class="prompt-text visible" id="prompt_{prompt_id}">{escaped_prompt}</div>
                    </div>
                </div>
"""

        html += """            </div>
        </div>
"""

    html += f"""
        <div class="footer">
            Generated by A/B Test Pipeline | Seedance 2.0 on Enhancor | {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
    <script>
        function togglePrompt(id) {{
            const el = document.getElementById('prompt_' + id);
            el.classList.toggle('visible');
            const toggle = el.previousElementSibling;
            toggle.textContent = el.classList.contains('visible') ? 'Hide prompt' : 'Show prompt';
        }}
        // Seek all videos to 0.5s for thumbnails (prevents black frames)
        document.querySelectorAll('video').forEach(v => {{
            v.addEventListener('loadeddata', () => {{
                if (v.currentTime < 0.1) v.currentTime = 0.5;
            }}, {{ once: true }});
        }});
    </script>
</body>
</html>"""

    report_path = project_dir / "report.html"
    with open(report_path, "w") as f:
        f.write(html)

    print(f"Report generated: {report_path}")
    print(f"Open in browser: file://{report_path}")
    return str(report_path)


def main():
    parser = argparse.ArgumentParser(description="Generate A/B test comparison dashboard")
    parser.add_argument("--matrix", required=True, help="Path to matrix.json")
    args = parser.parse_args()
    generate_report(args.matrix)


if __name__ == "__main__":
    main()
