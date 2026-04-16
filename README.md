# Seedance 2.0 AI UGC

Generate realistic AI UGC video ads with AI avatars — A/B test at scale using the Enhancor UGC 2.0 API, powered by Claude Code.

Create human-like talking head videos, product reviews, podcast clips, lifestyle commercials, and greenscreen TikToks with realistic AI-generated people. No actors, no studio, no restrictions. Just your product image and a prompt.

## What You Can Do

**AI Avatar Video Generation**
- Generate realistic talking humans that review your product, tell stories, and pitch directly to camera
- AI avatars with natural lip-sync, hand gestures, facial expressions, and body movement
- No actor needed — Enhancor UGC 2.0 creates photorealistic AI people from text descriptions or reference images
- Full creative control over appearance, setting, wardrobe, tone, and dialogue

**A/B Testing at Scale**
- Generate 2, 4, 8, or more video variants per product automatically
- Test different hooks: Authority vs. Story, Problem-Solution vs. Social Proof, Hook-first vs. Comparison
- Test different formats: Podcast (16:9), UGC (9:16), Lifestyle (9:16), Greenscreen TikTok (9:16)
- Test different durations: 4s to 15s per video
- Test different tones: Casual, Professional, Luxury, Educational, Edgy
- Side-by-side comparison dashboard to review all variants at once
- Track which angles perform best across campaigns

**4 Ad Formats Built In**

| Format | Aspect | Duration | What It Generates |
|--------|--------|----------|-------------------|
| Podcast Ad | 16:9 | 4-15s | AI avatar as podcast guest discussing your product with authority |
| UGC Ad | 9:16 | 4-15s | Realistic creator-style product review — selfie cam, bedroom/kitchen |
| Lifestyle Ad | 9:16 | 4-15s | Cinematic commercial — morning routines, active lifestyle, no dialogue |
| Greenscreen TikTok | 9:16 | 4-15s | Direct-to-camera pitch against bold colored backgrounds |

**Smart Asset Management**
- Drag-and-drop Control Center UI for organizing product images, AI avatar references, and mood boards
- AI vision analysis on every uploaded image — Claude understands your product and writes better prompts
- Structured asset library with auto-renaming and categorization

## How It Works

1. **`python3 setup.py`** — downloads project configuration
2. **`onboard`** — Claude asks about your product, audience, goals, discount codes
3. **Upload assets** — drag product images and avatar references into the Control Center (localhost:8092)
4. **`analyze my new assets`** — Claude analyzes each image with AI vision
5. **`ab-test`** — generates video ad variants using the Enhancor UGC 2.0 API
6. **Review** — compare all variants side-by-side in the output dashboard

## Setup

```bash
python3 setup.py
```

Then open the project in [Claude Code](https://claude.ai/code) and type `onboard`.

## Requirements

- [Claude Code](https://claude.ai/code)
- [Enhancor UGC API key](https://app.enhancor.ai/api-dashboard)
- Python 3

## Enhancor UGC 2.0 API

This project uses the [Enhancor UGC 2.0 API](https://enhancor.ai) for AI video generation.

- Generate cinema-grade video with synchronized audio and lip-sync
- Photorealistic AI avatars with natural movement and expressions
- Up to 9 reference images per generation for maximum control
- Support for UGC, multi-reference, lipsyncing, and text-to-video modes
- 16:9, 9:16, 4:3, 1:1, and 21:9 aspect ratios

**Pricing:**

| Model | Type | Resolution | Price | Credits |
|-------|------|-----------|-------|---------|
| Seedance 2 | No Video Input | 480p | **$0.089/s** | 89 CR/s |
| Seedance 2 | No Video Input | 720p | **$0.189/s** | 189 CR/s |
| Seedance 2 Fast | No Video Input | 480p | **$0.073/s** | 73 CR/s |
| Seedance 2 Fast | No Video Input | 720p | **$0.155/s** | 155 CR/s |
| Seedance 2 | With Video Input | 480p | **$0.052/s** | 52 CR/s |
| Seedance 2 | With Video Input | 720p | **$0.115/s** | 115 CR/s |
| Seedance 2 Fast | With Video Input | 480p | **$0.042/s** | 42 CR/s |
| Seedance 2 Fast | With Video Input | 720p | **$0.095/s** | 95 CR/s |

| Example | Cost |
|---------|------|
| 5s UGC video at 480p (no video input) | **$0.45** |
| 5s UGC video at 720p (no video input) | **$0.95** |
| 8-video A/B test (5s, 480p) | **~$3.56** |

**Up to 65% off market price** — the cheapest Seedance 2 Full Access API available. You cannot find this price anywhere else. Full Access means human face generation is enabled.

Failed generations are automatically refunded.

Get your Enhancor UGC API key at [app.enhancor.ai/api-dashboard](https://app.enhancor.ai/api-dashboard).

## Disclaimer

> The Enhancor UGC 2.0 API is experimental. Some generations may fail or produce unexpected results. Failed generations are automatically refunded.
>
> By using this tool, you agree to comply with all applicable terms of service and laws. You are solely responsible for the content you generate. Do not create videos using the likeness of real individuals without their explicit consent. Do not generate content featuring celebrities, public figures, or any person whose rights you do not hold.

## Commands

| Command | What It Does |
|---------|-------------|
| `onboard` | Set up your product profile — name, audience, goals, discount codes |
| `assets` | Analyze uploaded images with AI vision |
| `ab-test` | Generate A/B tested video ad variants |
| `analyze my new assets` | Analyze new images uploaded via the Control Center |

## Built With

- [Claude Code](https://claude.ai/code) — AI-powered development and orchestration
- [Enhancor](https://enhancor.ai) — UGC 2.0 video generation API
