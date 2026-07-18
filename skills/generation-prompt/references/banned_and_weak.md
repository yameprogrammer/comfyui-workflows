# Banned & weak prompt language

## 1. Hard ban (still + motion)

Do not use as primary content:

```
masterpiece, best quality, ultra detailed, 8k, 4k, uhd,
stunning, epic, gorgeous, beautiful cinematic, award winning,
unreal engine, octane render, trending on artstation,
perfect anatomy (without specifics), hyperrealistic 8k raw photo
```

“Cinematic” alone is banned; use **concrete light + lens + grade**.

## 2. Weak (replace)

| Weak | Stronger |
|------|----------|
| beautiful woman | mid-20s Korean woman, oval face, … |
| sad mood | eyes down on cup, mouth tight practiced smile |
| nice lighting | soft warm key camera left, cool window fill |
| cinematic shot | medium close-up, 85mm, eye level, shallow DOF |
| detailed background | rain-streaked window, oak counter mid-ground |
| high quality | (delete; add materials + focus) |

## 3. Motion-only bans (I2V/SI2V body)

```
wearing…, cream blouse, long hair description,
beautiful face, detailed eyes, makeup,
masterpiece, 8k, scene description of whole café restart
```

## 4. Risk: empty quality soup

If removing banned words leaves **&lt; 8 content words**, rewrite from SHOT fields.

---

## 5. Krea2 traps (still positive body)

Do **not** put these patterns in the **positive** `-p` string for Krea:

| Trap | Why | Use instead |
|------|-----|-------------|
| Long `NO / without / never` lists (`NO second person, NO poster…`) | Model may still visualize banned concepts; dilutes composition | Positive: `solitary woman`, `only one yellow parasol over her head` |
| Danbooru tag soup (`1girl, looking at viewer, …`) | Official + HF: natural language preferred | One prose paragraph |
| Meta wrappers (`In this image…`, `The photo shows…`) | Expansion/system prompts forbid | Start with subject or medium |
| Casting-plate merge (`plain light gray seamless backdrop` + outdoor store) | Causes white/grey studio ghosts outdoors | Scene architecture only |
| Dumping full negative list into positive | Same as NO-spam | Negative slot only, or omit |
| Over-long duplicate essays (&gt;512 tokens) | Truncation drops later clauses (community report) | 90–140 words, one pass |

**Allowed once as a short close (optional):**  
`Only one person and one yellow parasol.` — after positive locks are already clear.

Full dialect: `references/krea2_still_prompts.md`.

---

## 6. Cross-model mistakes

| Mistake | Why it fails |
|---------|----------------|
| Illustrious `masterpiece, 1girl` on Krea/Z-Image photoreal MV | Wrong dialect → taggy or off-style |
| Krea 140w still essay pasted into Wan/LTX I2V | Re-locks look, weak motion, identity fight |
| Qwen mega-edit (pose+wardrobe+bg+face) one shot | Drift; chain small edits |
| Ideogram free prose for critical brand spelling | Use typed `text` / `exactly reading` |
| Moody Turbo: trust long negative only | Turbo often ignores negatives — positive locks |
| I2V wardrobe/face essay | Image already owns identity |