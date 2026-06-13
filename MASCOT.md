# Mascot Design Brief — "The Deck"

*Companion to SPEC.md §8. For whoever draws the real pixel sprites. Decided June 12, 2026 with Bill.*

## The character
An **8/16-bit pixel-art reel-to-reel tape deck** that lives in the app's interface and is animated by what the player is doing. Inspiration: vintage blue Technics / Akai reel-to-reel decks (Technics RS-1500 in blue is the touchstone). It is a *machine with a face*, warm and characterful, in the same friendly spirit as the Claude Code pixel character — but its own creature, not a copy.

Working name: **"The Deck"** (final name TBD by Bill).

## Anatomy → face
- **Two reels = eyes.** Each reel is a **complete, fully-visible circle drawn IN FRONT of (on top of) the body**, mounted high so the reel's lower arc overlaps the body rectangle and its upper portion stands above the top edge. **Never clip the circle** — the whole round disc is always visible (this is how real Technics/Akai decks look; the reels are discs mounted on the face, not half-circles peeking over a wall). Draw order: body rectangle first, then the reel circles painted over it. The reel hub + spokes read as a pupil; the spokes rotating gives "life."
- **Two VU meters = eyebrows.** Small cream/amber rectangles on the face with a little red needle. Needle position acts as eyebrow expression and bounces with the music.
- **Transport button(s) = mouth.** A small pill/shape on the lower face that changes: flat (calm), curved-up (smile), small/pursed (effort).
- **Body = a wood-and-metal deck.** Blue face (Technics blue) with dark navy outline; optional thin wood-grain side.

## Palette (maps to the blue Technics look; theme-able later)
- Reel face / body: blue `#185FA5`, lighter reel `#85B7EB`, bright "playing" blue `#378ADD`
- Outlines / hubs: navy `#042C53`
- Spokes / highlights: pale blue `#E6F1FB`
- VU meter face: cream `#FAEEDA` (resting) / amber `#FAC775` (active)
- VU needle: red `#A32D2D`
- (When the app is themed, the mascot SHOULD recolor to match the active theme's accent — see SPEC §8b.)

## Core animation states (minimum set)
1. **Idle / paused:** reels still, needles resting near center, mouth flat. Occasional slow blink (reels briefly become flat lines) or a tiny "Zzz" after long idle.
2. **Playing:** reels **rotate** (spokes turning), VU needles **bounce** (a simple loop is fine; true beat-sync is a future MAY), VU faces glow amber, mouth curves into a smile.
3. **Searching / scanning library:** reels **squint** (eyes narrow to slits), a small "..." or tape-threading motion on the face, mouth small with effort — "working."
4. **Track change:** a brief reaction — reels do a quick spin-up, a little "ftwd" flick, or the whole body hops once.

## Implementation (from SPEC §8)
- Sprite-sheet PNGs, **32×32 or 48×32** frames (the deck is wider than tall; pick a size that fits the reels-above-body silhouette). Integer/nearest-neighbor scaling only — crisp pixels, never blurred.
- A small **JSON** describes states → frame ranges → frame durations, so new animations drop in without touching core code.
- Home perch: the **now-playing bar**. MAY wander along the bottom edge. Because it's a deck (a machine, not a walker), it leans toward *perch-and-react* rather than strolling — that's fine and on-brand.
- MUST be disable-able in Settings. Default on.

## Notes / open questions
- The reels-as-eyes spin is the star animation and comes almost free from "is playing." Prioritize it.
- VU-needle bounce is "good but not perfect" per Bill — acceptable; refine later.
- Real pixel art replaces the vector stand-ins sketched in chat June 12, 2026.
