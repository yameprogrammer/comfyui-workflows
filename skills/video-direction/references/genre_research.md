# Genre / format research → minimal recipe set

- **Date**: 2026-07-16  
- **Output**: [genre_recipes.md](genre_recipes.md) L0/L1/L2  
- **Principle**: Academic genre theory explains *hybridization* and *conventions*; production needs *formats* that change shot lists and audio contracts. We map both, then keep **12 L1 recipes**.

---

## 1. Academic / textbook lines (what they actually give us)

| Source / idea | Claim (compressed) | Factory implication |
|---------------|--------------------|---------------------|
| **Alan Williams** (via film genre surveys) | Broad cinema buckets: **narrative / avant-garde / documentary** | L1 splits fiction drama (R02), mood-experimental (R08), observational (R07) — not 50 theme genres |
| **Bordwell & Thompson** (*Film Art*) | Genres = **types** audiences and makers recognize by **recurring conventions**; films often **straddle** genres | Do not force pure labels; allow **recipe + tone modules** |
| **Janet Staiger** | Genre defined by ideal / empirical / a priori / **social convention** methods | L1 names follow **what practitioners call the job**, not only theme |
| **Hybridization** (Collins et al., Hollywood practice) | Modern works blend genres | Gate 0 picks **one primary L1**, attaches L2 modules |
| **Eric R. Williams — Screenwriters Taxonomy** | Layers: film type (comedy/drama) · **super-genre** (action, horror, romance, SF, thriller, crime, fantasy, slice-of-life, sports, war, western…) · voice (musical, animation…) | Super-genres become **L2 tone**, not 11 separate factory pipes. Film type (comedy) → R09; horror/thriller → R10; slice-of-life → R01/R02 |
| **Genre as schema** (narrative psychology / popular movies research) | Audience predicts by genre schema | CREATIVE anti-list + motif = manage expectation; hook contract test |

**Takeaway for us:** Academic “genre” is multi-axial and hybrid. A factory skill must not enumerate super-genres as separate CLIs; it should enumerate **production formats**.

---

## 2. Industry feature / catalogue practice

| Source | Classification habit | Mapping |
|--------|---------------------|---------|
| Studio / festival catalogues | Drama, comedy, horror, thriller, doc, animation, music… | Theme tags → L2 or soft labels in CREATIVE “genre of feeling” |
| **StudioBinder** shot-list practice | Not genre encyclopedias — **coverage, shot size, MV section jobs** | Shot grammar + R03 section map |
| Commercial production | Spot / branded content / music video / social | R06, R08, R03, R05 |

---

## 3. Contemporary short-form / social practice (2024–2026)

Platform and creator ops rarely use “Western vs Noir”. They use **job + platform + length**:

| Practitioner bucket (common) | Typical length | Our L1 |
|------------------------------|----------------|--------|
| Talking head / skit / storytime | 15–60s | R01, R02, R09 |
| Trend / dance / challenge | 15–30s | R04 |
| Music / performance cut | 15–60s+ | R03 |
| Product / UGC / GRWM-adjacent demo | 15–45s | R06 |
| Educational / tips / myth-bust | 30–60s (Shorts strong) | R11 |
| Lifestyle / aesthetic / BTS | 15–30s | R07, R08 |
| Hook-first viral | 15–30s peak market share band | R05 (overlay) |
| Branded mood / filmic ad | 15–60s | R08 |

Notes from short-form industry writing (TikTok / Reels / Shorts strategy summaries):

- **Vertical 9:16** dominant for social; completion-sensitive.  
- **15–30s** often treated as commercial sweet band; structure still needs hook → payoff.  
- Content-type lists repeat: **tips, demo, dance, comedy, storytelling, lifestyle, product** — these informed R05–R11, R04, R09, R01–R02, R06–R08.

This is **format coverage**, not academic super-genre coverage.

---

## 4. Mapping: academic super-genre → our minimal set

| Super-genre / type (Williams-like) | Primary L1 | L2 modules (examples) |
|------------------------------------|------------|------------------------|
| Slice of life / everyday drama | R01, R02 | motif, one-take |
| Romance (as feeling) | R02, R08 | motif, soft light |
| Comedy | R09 | reaction_cut |
| Horror | R10 | delay_reveal |
| Thriller / mystery | R10, R02 | delay_reveal |
| Action | R02 + motion-heavy | chorus_event-like peaks |
| Fantasy / SF | R02, R08 | world insert density |
| Musical (voice) | R03 | lip_hero_sparse |
| Documentary | R07 | insert_prop |
| Sports | R04-like body / R02 | full body coverage |
| Western / war / crime | R02 + R10 tone | axis, delay |
| Branded / commercial | R06, R08 | scroll_hook |
| Music video | R03 | chorus_event |
| Dance challenge | R04 | — |

---

## 5. Why exactly 12 L1 recipes?

| Criterion | Result |
|-----------|--------|
| Covers factory modes (story/mv/hybrid/dance/visual) | Yes via L0 |
| Covers social practitioner content types | Yes (talk, drama, music, dance, product, edu, lifestyle, comedy) |
| Covers academic narrative vs nonfiction vs performance | R02 / R07 / R03–R04 |
| Avoids theme explosion | Horror≠separate from thriller pressure (R10) |
| Leaves room to grow | New L1 only after 3+ real channel repeats |

**Not in the 12 (on purpose):** pure pure-infographic, multi-cam live sports broadcast, feature coverage packages, game cinematic full pipelines.

---

## 6. How agents should use research

1. Do **not** ask the user “which of 40 genres?”  
2. Run Gate 0 cheat sheet in `genre_recipes.md` §3.  
3. Write into CREATIVE / SHOT_DESIGN:

```yaml
L0: M_hybrid
L1: R01_talking_performance_short
L2: [mod_insert_prop, mod_motif_trinity]
genre_of_feeling: "wet loneliness + soft service comedy"
```

4. Theme words (horror, romance) go in **genre_of_feeling** + L2, not as fake L1 ids.

---

## 7. References (for humans; no full-text copy)

- Film genre overview — narrative / documentary / experimental distinctions; hybridization; Screenwriters Taxonomy super-genres (public encyclopedic summaries of Williams / Staiger / Bordwell–Thompson discussions).  
- StudioBinder — shot list & music video shot-list practice.  
- Short-form platform strategy articles (TikTok / Reels / Shorts content-type and length bands, 2025–2026 practitioner literature).  
- Prior factory docs: `docs/video_director_master_persona.md`, `docs/audio_motion_production_modes.md`, `docs/dance_challenge_pipeline_design.md`.  
- Agent skill process patterns: gated director / multi-shot storyboard skills (see parent `RESEARCH.md`).

Update this file when adding an L1 recipe so the “why this number” stays honest.