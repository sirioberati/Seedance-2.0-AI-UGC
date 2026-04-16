---
name: asset-wizard
description: "Asset library wizard for organizing product images, subject/influencer images, and mood references. Scans inbox or Control Center uploads, classifies with vision, renames, analyzes, and builds a registry. Trigger on: /assets, organize assets, add images, sort images, asset library, manage images, analyze assets"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Asset Library Wizard

Organize and analyze images for the A/B test pipeline. Images can be uploaded via the Control Center (localhost:8099) or dropped into `assets/inbox/`.

## Trigger Phrases

- `/assets`
- "organize assets"
- "add images"
- "sort images"
- "analyze assets"

## Folder Structure

```
assets/
├── inbox/          ← Drop raw images here (or upload via Control Center)
├── products/       ← Product images (sorted by slug)
├── subjects/       ← Human/influencer images (sorted by slug)
├── moods/          ← Lifestyle/mood images (sorted by slug)
├── backups/        ← Original copies of every uploaded image
└── registry.json   ← Master index with AI context per image
```

## Workflow

IMPORTANT: Every time this skill triggers, you MUST analyze any new images that were uploaded via the Control Center. Users expect that once they upload in the UI, the image is fully processed — including AI context. Never skip Step 1.

### Step 1: Auto-Analyze Any New Uploads

Check for images missing AI context:
```bash
python3 .claude/skills/ab-test-pipeline/scripts/save_context.py pending
```

If images need analysis, go to Step 4. If the inbox has new images, continue to Step 2.

### Step 2: Scan Inbox

```bash
python3 .claude/skills/ab-test-pipeline/scripts/asset_wizard.py scan
```

If inbox is empty, tell the user: "Upload images via the Control Center at http://localhost:8099 or drop files into assets/inbox/"

### Step 3: Classify & Sort Each Image

For EACH image in the inbox:

1. **Read the image** using the Read tool (you have vision — you can see images)
2. **Classify it** as PRODUCT, SUBJECT, or MOOD
3. **Ask the user** to confirm the category and name via conversation
4. **Sort it**:
```bash
python3 .claude/skills/ab-test-pipeline/scripts/asset_sort.py \
  --file "assets/inbox/{filename}" \
  --type "product" \
  --slug "ag1" \
  --name "AG1" \
  --description "Daily greens supplement"
```

### Step 4: Analyze Every Image (CRITICAL)

After sorting, you MUST analyze every image that has `ai_context: null` in the registry. This context is what makes the prompts good.

For EACH unanalyzed image:

1. **Read the image** with the Read tool to see it
2. **Generate a structured analysis** based on the category:

**For PRODUCTS** — describe:
- product_type, brand_visible, colors, packaging, key_features, background, shot_angle
- ad_notes: how to reference this in a Seedance 2 prompt

**For SUBJECTS** — describe:
- gender, age_range, appearance, expression, clothing_style, setting
- best_for: which ad formats suit this person (UGC, podcast, greenscreen, lifestyle)
- ad_notes: how to describe this person in a prompt so the AI matches their look

**For MOODS** — describe:
- setting, lighting, color_palette, mood, time_of_day, style_reference
- best_for: what product categories pair with this aesthetic
- ad_notes: how to use as @image2/@image3 mood reference in lifestyle prompts

3. **Save the context**:
```bash
python3 .claude/skills/ab-test-pipeline/scripts/save_context.py save \
  --path "assets/products/ag1/ag1-product-01.png" \
  --context '{"product_type":"greens supplement","brand_visible":"AG1","colors":"green pouch, white label","packaging":"stand-up pouch with scoop","key_features":"nutrition facts panel, 75 servings label","background":"white studio","shot_angle":"front-facing, slight angle","ad_notes":"Show the green pouch prominently. Reference the scoop and mixing action. The green color pops against neutral backgrounds."}'
```

### Step 5: Summary

```bash
python3 .claude/skills/ab-test-pipeline/scripts/asset_wizard.py status
```

Show the user what was processed and confirm all images now have AI context.

## Classification Guide

**PRODUCT**: Packaging, bottle, box, device, app screenshot — no human face as primary subject
**SUBJECT**: Person, human face, portrait, influencer — person is the primary focus
**MOOD**: Landscape, interior, lifestyle scene — no specific product or face focus

## After Control Center Uploads

When users upload via the Control Center (localhost:8099), the files get sorted automatically but `ai_context` is set to `null`. The user should then run `/assets` so Claude can analyze the new images and populate the context. This is the key step that makes prompt generation intelligent.
