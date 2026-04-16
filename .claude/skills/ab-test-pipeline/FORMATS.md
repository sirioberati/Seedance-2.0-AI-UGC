# Ad Format Specifications

## Format Matrix

| Format | Enhancor Mode | Aspect Ratio | Duration | Image Slots | Audio | Key Requirement |
|--------|--------------|--------------|----------|-------------|-------|-----------------|
| Podcast Ad | UGC | 16:9 | 4-15s (user choice) | @image1 (product) | @audio1 (optional) | Studio setting, 2 people, interview feel |
| UGC Ad | UGC | 9:16 | 4-15s (user choice) | @image1 (product) | @audio1 (optional) | Phone-shot feel, single creator, authentic |
| Lifestyle Ad | Multi Reference | 9:16 | 4-15s (user choice) | @image1 (product) + @image2 + @image3 (mood) | @audio1 (optional) | Cinematic, no dialogue, aspirational |
| Greenscreen TikTok | UGC | 9:16 | 4-15s (user choice) | @image1 (product) | @audio1 (optional) | Solid color BG, direct-to-camera, fast pace |

## Audio References

When an audio reference is selected (voice sample from the registry), append this line to EVERY prompt:

> Reference @audio1 as the exact voice, pacing, and emotional delivery. Always reference @audio1.

The audio file is uploaded to temporary hosting and sent as the `audios` field (string array) in the Enhancor API payload. This tells Seedance 2 to match the voice characteristics of the reference audio.

## Enhancor API Payload Per Format

All payloads use `type: "image-to-video"` and include `prompt`, `webhook_url`, and `full_access: true`.
Audio is ALWAYS sent via the top-level `audios` field (string array), not nested inside images.

### Podcast Ad
```json
{
  "type": "image-to-video",
  "mode": "ugc",
  "aspect_ratio": "16:9",
  "duration": "15",
  "full_access": true,
  "products": ["https://...product.png"],
  "influencers": ["https://...subject.jpg"],
  "audios": ["https://...voice.mp3"]
}
```

### UGC Ad
```json
{
  "type": "image-to-video",
  "mode": "ugc",
  "aspect_ratio": "9:16",
  "duration": "15",
  "full_access": true,
  "products": ["https://...product.png"],
  "influencers": ["https://...subject.jpg"],
  "audios": ["https://...voice.mp3"]
}
```

### Lifestyle Ad
```json
{
  "type": "image-to-video",
  "mode": "multi_reference",
  "aspect_ratio": "9:16",
  "duration": "15",
  "full_access": true,
  "images": ["https://...product.png", "https://...mood1.png", "https://...mood2.png"],
  "audios": ["https://...voice.mp3"]
}
```

### Greenscreen TikTok
```json
{
  "type": "image-to-video",
  "mode": "ugc",
  "aspect_ratio": "9:16",
  "duration": "10",
  "full_access": true,
  "products": ["https://...product.png"],
  "influencers": ["https://...subject.jpg"],
  "audios": ["https://...voice.mp3"]
}
```

### UGC Mode Limits
- Combined `products` + `influencers` + `images` ≤ 9 images
- Up to 3 `videos` and 3 `audios` per request

## Variant Angle Assignments

| Format | Variant A Angle | Variant B Angle |
|--------|----------------|-----------------|
| Podcast Ad | Authority/Expert | Story/Transformation |
| UGC Ad | Problem-Solution | Social Proof |
| Lifestyle Ad | Morning Ritual | Active Lifestyle |
| Greenscreen TikTok | Hook-first | Comparison |

## Output Naming Convention

```
{format_slug}-v{variant_number}.mp4
```

Examples:
- `podcast-v1.mp4`, `podcast-v2.mp4`
- `ugc-v1.mp4`, `ugc-v2.mp4`
- `lifestyle-v1.mp4`, `lifestyle-v2.mp4`
- `greenscreen-v1.mp4`, `greenscreen-v2.mp4`
