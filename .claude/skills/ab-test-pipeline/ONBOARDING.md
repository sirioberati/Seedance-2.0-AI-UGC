---
name: onboarding-wizard
description: "Onboarding wizard for the UGC Ad Pipeline. Walks users through API setup, Control Center, product profile, goals, and assets. Trigger on: onboard, get started, set up, new product, onboarding, configure product, add brand"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Onboarding Wizard

Walk new users through the complete setup — from API key to first ad generation.

## Trigger Phrases

- "onboard"
- "get started"
- "set up"
- "new product"
- "onboarding"

## Workflow

Follow these steps exactly in order. This is the user's first experience — make it clear and helpful.

### Step 1: Welcome + API Key Setup (FIRST THING)

Display:
```
Welcome to Seedance 2.0 AI UGC!

I'll help you set up everything in about 2 minutes.
Let's start with the most important thing — your API key.
```

Check if API key exists:
```bash
test -f .env && grep -q "ENHANCOR_API_KEY=." .env && echo "API key configured" || echo "API key NOT configured"
```

If NOT configured, display:
```
To generate AI video ads, you need an Enhancor UGC Full Access API key.

  Get your key here: https://app.enhancor.ai/api-dashboard

  Up to 65% off market price — the cheapest Seedance 2 Full Access API
  available. You cannot find this price anywhere else.
  Full Access means human face generation is enabled.

  1. Go to https://app.enhancor.ai/api-dashboard
  2. Create an account and choose a plan
  3. Copy your API key from the dashboard

Pricing (per second):
  Seedance 2 (No Video Input):
    480p — $0.089/s (89 CR/s)
    720p — $0.189/s (189 CR/s)
  Seedance 2 Fast (No Video Input):
    480p — $0.073/s (73 CR/s)
    720p — $0.155/s (155 CR/s)
  Seedance 2 (With Video Input):
    480p — $0.052/s (52 CR/s)
    720p — $0.115/s (115 CR/s)
  Seedance 2 Fast (With Video Input):
    480p — $0.042/s (42 CR/s)
    720p — $0.095/s (95 CR/s)

  Example costs:
    5s UGC video at 480p (no video input) = $0.45
    5s UGC video at 720p (no video input) = $0.95
    8-video A/B test (5s each, 480p)      = ~$3.56

  Top-up credits available.
  Failed generations are automatically refunded.

Once you have your key:
  1. Run: cp .env.example .env
  2. Open the .env file
  3. Paste your key next to ENHANCOR_API_KEY=
```

Wait for the user to confirm they've set up the key, or they say "skip" / "later".

Then display the disclaimer:
```
Disclaimer: The Enhancor UGC 2.0 API is powered by ByteDance's
Seedance model. Video generation is experimental — some generations
may fail or produce unexpected results. Failed generations are
automatically refunded. By proceeding, you agree to comply with
ByteDance's terms of service. Do not create videos using the
likeness of real individuals without their explicit consent.
```

If key IS already configured, say: "API key is set up. You're good to go."

### Step 2: Launch & Explain the Control Center

Start the Control Center server (try Python first, fall back to Node.js if Python can't bind ports):
```bash
python3 .claude/skills/ab-test-pipeline/scripts/asset_server.py &
sleep 3
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8099 | grep -q 200; then
  # Python server failed to start — fall back to Node.js
  node server.js &
  sleep 2
fi
```

Then display:
```
Your Control Center is now running at http://localhost:8099

The Control Center is a local dashboard in your browser where you
manage all your creative assets. Here's what it does:

UPLOAD ZONE (top)
  Three drag-and-drop zones for your images:
  - Products — photos of your product, packaging, bottles, devices
  - Subjects — influencer photos, creator headshots, AI avatar references
  - Moods — lifestyle scenes, aesthetic references, mood boards

  Drop images into the right zone, give them a name, and click Add.
  Files are automatically renamed, organized into folders, and registered.

LIBRARY (middle)
  Shows all your organized assets with thumbnails. You can:
  - Add more images to existing groups
  - Remove images you don't need
  - See AI analysis context for each image (after Claude analyzes them)

OUTPUTS (bottom)
  After you run ad generation, your videos appear here:
  - Video players for each generated ad
  - Grouped by product and run
  - Side-by-side comparison of all variants
  - Links to full A/B test reports

The Control Center handles data — uploading, organizing, previewing.
All the smart work (prompts, generation, analysis) happens here in
Claude. You'll go back and forth between the two.

Go ahead and open http://localhost:8099 in your browser now.
```

### Step 3: Product Profile (ONE question at a time)

Ask each question individually using AskUserQuestion. Give examples and recommendations so users can click to select if they're unsure. NEVER combine multiple questions.

**Q1: Product Name**
Ask: "What's your product called?"
Example hint: "e.g. AG1, Rhode, Dyson Airwrap, Midday Squares"
(Free text — no options needed)

**Q2: Category**
Ask: "What category best describes your product?"
Use AskUserQuestion with options:
- Supplement — vitamins, protein, greens, wellness powders
- Skincare — serums, moisturizers, masks, SPF
- Fashion — clothing, shoes, accessories, jewelry
- Tech — gadgets, apps, devices, software
- Food & Beverage — snacks, drinks, meal kits, coffee
- Fitness — equipment, wearables, gym accessories
- Other

**Q3: Description**
Ask: "Describe your product in one sentence."
Show examples based on their category:
- Supplement: "Daily greens supplement with 75 vitamins and minerals"
- Skincare: "Peptide lip tint with built-in phone case holder"
- Fashion: "Lightweight running jacket with reflective print"
- Tech: "AI-powered photo editing app with one-tap filters"
- Food: "Functional chocolate bar with 20g protein"

**Q4: Selling Points**
Ask: "What are the top 3-5 benefits? List them one per line or comma-separated."
Show examples based on their category:
- Supplement: "75 vitamins and minerals, Supports energy and focus, Gut health and immunity"
- Skincare: "Hydrates for 24 hours, Dermatologist tested, No parabens"
- Fashion: "Water resistant, Ultra lightweight, Reflective for night runs"
If the user seems stuck, suggest: "Think about what makes someone buy this instead of a competitor. What do your best reviews mention?"

**Q5: Price Point**
Ask: "What's the price point?"
Use AskUserQuestion with options:
- $ Budget (under $25) — "Ads will feel accessible and casual"
- $$ Mid-range ($25-$100) — "Balanced between quality and value" (Recommended)
- $$$ Premium ($100+) — "Ads will feel aspirational and luxurious"

**Q6: Differentiator**
Ask: "What makes your product different from competitors? One sentence."
Show examples:
- "Most comprehensive daily nutrition in one scoop"
- "Only lip product that clips into your phone case"
- "The only running jacket with full 360 reflective print"
If the user is stuck, suggest: "What would you say if someone asked 'why this one and not the other brands?'"

### Step 4: Audience & Goals (ONE question at a time)

**Q7: Target Audience**
Ask: "Who is your ideal customer?"
Show examples and suggest based on their category:
- Supplement: "Health-conscious adults 25-45, into fitness and wellness"
- Skincare: "Women 18-35, beauty-focused, follow skincare influencers"
- Fashion: "Active men and women 20-40, runners, outdoor enthusiasts"
- Tech: "Content creators 18-30, social media savvy"
If the user gives a short answer like "women 25-35", ask: "What are their interests? e.g. fitness, beauty, cooking, tech"

**Q8: Ad Goal**
Ask: "What's the primary goal for these ads?"
Use AskUserQuestion with options:
- Conversion (Recommended) — "Get people to buy. Direct CTAs, discount codes, urgency."
- Awareness — "Get your brand seen. Broader reach, memorable visuals."
- Consideration — "Get people interested. Product demos, comparisons, reviews."
- Retargeting — "Re-engage people who already visited. Social proof, reminders."

**Q9: Platforms**
Ask: "Which platforms are you running ads on?"
Use AskUserQuestion with multiSelect:
- TikTok — "9:16 vertical, fast-paced, hook in first 2 seconds"
- Instagram Reels — "9:16 vertical, polished but authentic"
- YouTube Shorts — "9:16 vertical, slightly longer hooks OK"
- Facebook — "Mixed formats, slightly older audience"
Recommend: "TikTok + Instagram Reels is the most common combo"

**Q10: Tone**
Ask: "What vibe should the ads have?"
Use AskUserQuestion with options:
- Casual / Fun (Recommended) — "Natural, relatable, like a friend recommending it. Best for UGC."
- Professional — "Clean, polished, trust-building. Good for B2B or premium health."
- Luxury — "Aspirational, cinematic, premium feel. Best for high-end products."
- Educational — "Informative, ingredient-focused, science-backed. Good for supplements."
- Edgy — "Bold, provocative, pattern-interrupt. Best for younger audiences."

**Q11: Discount Code** (optional)
Ask: "Do you have a discount code to include in the ads?"
Show example: "e.g. SAVE20 for 20% off, or FREE shipping with code SHIP"
Use AskUserQuestion with options:
- Yes, I have a code — then ask for code + what it gives
- No discount code — skip
- I'll add one later — skip

**Q12: Custom Notes** (optional)
Ask: "Any specific phrases, brand guidelines, or things you want in every ad?"
Show examples:
- "Always mention 'clinically tested'"
- "Never say 'cheap' — say 'affordable'"
- "End every ad with 'Link in bio'"
- "Use the tagline 'Fuel your day'"
Use AskUserQuestion with options:
- Yes, I have notes — then ask for the notes
- No, generate freely — skip

**Q13: Competitors** (optional)
Ask: "Name 1-3 competitor brands you're going up against or admire."
Show example: "e.g. Bloom, Liquid IV, Erewhon"
Use AskUserQuestion with options:
- Yes — then ask for names
- Skip — no competitors to mention

### Step 5: Save Brand Profile

Build the slug from the product name (lowercase, hyphenated). Save:
```bash
python3 .claude/skills/ab-test-pipeline/scripts/onboard.py save \
  --slug "{slug}" \
  --name "{name}" \
  --category "{category}" \
  --description "{description}" \
  --selling-points "{sp1},{sp2},{sp3}" \
  --price-point "{price}" \
  --differentiator "{diff}" \
  --age-range "{age}" \
  --gender "{gender}" \
  --interests "{interests}" \
  --objective "{goal}" \
  --platforms "{platforms}" \
  --tone "{tone}" \
  --discount-code "{code}" \
  --discount-details "{details}" \
  --custom-notes "{notes}" \
  --custom-cta "{cta}" \
  --competitors "{comp1},{comp2}"
```

### Step 6: Upload Assets

Display:
```
Brand profile saved!

Now upload your images in the Control Center at http://localhost:8099

You need at least:
  1 product image — a clear photo of your product

Optional (but makes ads much better):
  Subject images — influencer/creator photos for the AI avatar to reference
  Mood images — lifestyle scenes that set the visual tone

After uploading, come back here and say:

  analyze my new assets

I'll look at each image with AI vision and save detailed context
about what's in it — colors, packaging, features, how to reference
it in prompts. This makes your generated ads significantly better.
```

### Step 7: Summary

Show the complete profile:
```
Setup Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Product:    {name} — {description}
Category:   {category}
Price:      {price_point}
Unique:     {differentiator}

Benefits:
  1. {sp1}
  2. {sp2}
  3. {sp3}

Audience:   {gender}, {age_range}
Interests:  {interests}
Goal:       {objective}
Platforms:  {platforms}
Tone:       {tone}
{discount if any}
{competitors if any}

What's Next:
  1. Upload images in the Control Center (http://localhost:8099)
  2. Come back and say "analyze my new assets"
  3. Then say "ab-test" to generate your first video ads
```

## Example Onboarding Conversation

Here's what a typical onboarding looks like:

```
User: get started

Claude: Welcome to Seedance 2.0 AI UGC!
        Let's start with the most important thing — your API key.
        Go to https://app.enhancor.ai/api-dashboard to get yours.
        Pricing: Seedance 2 from $0.089/s (480p), $0.189/s (720p). Fast mode and video input options available at lower rates...

User: ok I got my key and added it to .env

Claude: API key confirmed! Now let me start your Control Center...
        Your Control Center is running at http://localhost:8099
        [explains what it does]
        Open it in your browser — I'll wait.
        Now let's set up your product. What's it called?

User: AG1

Claude: What category is AG1?
        [Supplement / Skincare / Fashion / Tech / Food / App / Other]

User: Supplement

Claude: Describe AG1 in one sentence.

User: Daily greens supplement with 75 vitamins and minerals

Claude: What are the top 3-5 selling points?

User: 75 vitamins, supports energy and focus, gut health

Claude: What's the price point? [$ / $$ / $$$]

User: $$

Claude: What makes AG1 different from competitors?

User: most comprehensive daily nutrition in one scoop

Claude: Who's your target audience?

User: health conscious adults 25-45

Claude: What's the primary goal? [Awareness / Conversion / ...]

User: Conversion

Claude: Which platforms? [TikTok / Instagram Reels / YouTube / Facebook]

User: TikTok, Instagram Reels

Claude: What tone? [Casual / Professional / Luxury / Educational / Edgy]

User: Casual/Fun

Claude: Any discount code?

User: SAVE20 for 20% off

Claude: Brand profile saved!
        Now upload your images in the Control Center at localhost:8099
        Then come back and say "analyze my new assets"
```
