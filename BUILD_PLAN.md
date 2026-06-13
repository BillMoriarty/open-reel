# Build Plan — Which model builds what, in what order

*Companion to SPEC.md. Decided with Bill, June 12, 2026. The honest division of labor for actually building the app.*

## The headline truth
No single model builds this whole app correctly in one shot — it's a real application (GStreamer pipeline + GTK4 UI + background scanner + SQLite cache + sprite animation + MPRIS + theming + notes), dozens of files. The question isn't "which model writes it" but "which model does which piece, and who holds the architecture together." Biggest risk with ANY model: asking for too much at once. Build one step at a time, test each before the next.

## Who's good at what
- **Haiku** — fast, cheap, shallow reasoning. Great at *well-specified, self-contained modules* (the scanner, the SQLite data-access layer, the theme loader). NOT the architect — it can't hold the whole system consistent. A good bricklayer.
- **Sonnet** — the workhorse for this build. Reasons well enough to keep architecture coherent across files; strong on this exact stack (Python/GTK/GStreamer); far cheaper than a frontier model. Write the bulk of the app here.
- **Opus (me)** — best spent on the *thinking*: architecture, the hard 10% (tags-vs-folders resolution, gapless pipeline, threading so the scan doesn't freeze the UI), code review, and untangling stubborn bugs. Too expensive for routine code.
- **Fable** — leave aside for engineering; its place is the **mascot**: pixel-art sprites and animation feel for "The Deck" (a creative-craft track, not systems).

## Recommended division of labor
Opus drafts the architecture/file plan → Sonnet writes most of the app against it → Haiku knocks out the isolated modules to keep costs down → Opus reviews and fixes the hard parts → mascot art runs as its own creative track (Fable or a pixel artist).

## Step-by-step plan (follow SPEC §12 order; test each before moving on)

| # | Step | Suggested model | Test before moving on |
|---|------|-----------------|------------------------|
| 0 | Architecture + file/module plan (the skeleton's shape, threading model, how modules talk) | **Opus** | A written plan Sonnet can follow; no code yet |
| 1 | Project skeleton: Python package, GTK4 window opens, dependency check | **Sonnet** | App launches, empty window appears |
| 2 | Config + folder picker (onboarding screen) | **Sonnet** | Pick a folder, path saved to config |
| 3 | Scanner: walk folders, read tags (mutagen), write SQLite, background thread + progress bar | **Haiku** (isolated) → **Opus** reviews threading | Scans a test folder without freezing UI; rows in DB |
| 3a | Tags-vs-folders resolution rule (SPEC §6) — the tricky grouping logic | **Opus** | Mismatched-tag album groups by tag; 2-disc album merges to one |
| 4 | Album grid view from cache; click-through to track list | **Sonnet** | Grid shows covers; click opens tracks |
| 5 | GStreamer playback: play/pause/seek/next/prev, gapless, now-playing bar w/ click+drag scrubber & volume | **Sonnet** for UI, **Opus** for the gapless pipeline | Plays a file; gapless between tracks; scrubber+volume drag works |
| 6 | Search bar, live filtering across cache | **Sonnet** | Ctrl+F, type 3 letters, song appears + plays on Enter |
| 7 | Queue panel, drag-and-drop reorder, album grouping | **Sonnet** | Queue reorders by drag; albums grouped as units |
| 8 | Mascot system: sprite renderer + state machine + core animations | **Sonnet** (system) + **Fable**/artist (art) | Mascot changes for paused/playing/scanning; toggle-off works |
| 9 | Theming: load plain-text theme files → GTK CSS, live switcher | **Haiku** (isolated) | Switch theme live; drop-in theme file appears in picker |
| 10 | Notes: plain `.md` per artist/album/song, editor pane, indicators | **Haiku** (isolated) → **Opus** spot-check | Note creates readable `Artist - Album - Song.md` in `~/Music Notes/`, survives cache delete |
| 11 | MPRIS + media keys + restore-last-session | **Sonnet** | Shows in GNOME shell; media keys work; queue restores |
| 12 | Settings (folders, rescan, toggle mascot, font, theme, notes folder) | **Haiku** (isolated) | Each setting persists and takes effect |
| 13 | Flatpak packaging + LICENSE (GPL-3.0) + README | **Sonnet** | Builds and runs as a Flatpak |
| ✓ | Full acceptance pass (SPEC §13) | **Opus** review | All §13 checks pass; diff music folder before/after = unchanged |

## How to actually drive it
For each row: paste SPEC.md (or the relevant section) + that one step's instruction into the chosen model. Get it working and tested before the next row. When something is stubborn or architectural, escalate that step to Opus rather than fighting it in a weaker model.

## Bottom line on "can Haiku make it?"
Haiku can make *several of the pieces* (steps 3, 9, 10, 12) well. It cannot reliably make the *whole app* or the hard architectural parts. The cost-smart, quality-smart path is Sonnet for the bulk, Haiku for the isolated modules, Opus for the architecture + hard 10% + final review, and a creative track for the mascot art.
