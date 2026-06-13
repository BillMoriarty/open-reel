# Build Spec — Fedora Local Music Player

**Status:** Specification, ready to build.
**Authored by:** Opus (planning), June 12, 2026.
**Intended builder:** A code-generation model (e.g. Haiku) implementing directly from this file.
**Owner:** Bill Moriarty.

This file is the single source of truth for *what to build*. Read it top to bottom. Every "MUST" is a hard requirement; every "SHOULD" is a strong preference; "MAY" is optional/future. When a choice isn't specified here, prefer the simplest, most boring, longest-lived option.

---

## 1. What this is (one paragraph)
A native, lightweight desktop music player for Fedora Linux that plays a personal library of local audio files (FLAC, MP3, OGG, M4A/AAC, WAV, Opus). It reads folders of files the user already owns; it never reorganizes or rewrites those files. The experience is **search-first** with **album art**, dressed in a **monospace/console aesthetic**, and animated by a small **8/16-bit pixel mascot** that lives in the interface. It must feel snappy on a library of several thousand tracks. Cross-platform (Linux first; macOS/Windows are a bonus, not a requirement).

---

## 2. Non-negotiable principles (the spine)
1. **Folders are the source of truth.** The app reads the user's audio files and their embedded tags. It MUST NOT write to, move, rename, or re-tag the user's files. Ever. (A future explicit "tag editor" feature could, but only on explicit user action and clearly separated — not in v1.)
2. **The cache is disposable.** For speed, the app keeps a single **SQLite** file as a *cache/index* of what it scanned. Deleting this file MUST cause a clean rebuild from the folders with zero data loss. The cache is a convenience, never the truth.
3. **Tags beat folders.** Embedded metadata is trusted first; folder structure is only a fallback and grouping hint. (See §6 — this is the rule that prevents the Picard-style "folder says one thing, tags say another" pain.)
4. **Boring, durable tech.** Time-tested libraries, plain files, human-readable code, descriptive variable names. No bleeding edge. No heavy abstraction layers.
5. **Native and light.** Not Electron. Not a blown-up phone UI. Starts fast, stays responsive, shows up in the desktop as a real media player.

---

## 3. Tech stack (decided)
- **Language:** Python 3.11+ (readable, the builder writes it reliably, decades-proven for this exact app class — see Quod Libet).
- **Audio engine:** **GStreamer** (via `python-gobject` / `gi`). This gives format support and **gapless playback** for free. Do not write custom audio decoding.
- **GUI toolkit:** **GTK4 + Libadwaita** (via `gi`). Native on Fedora/GNOME, cross-platform capable.
- **Tag reading:** **mutagen** (pure-Python, reads all target formats' tags and embedded cover art).
- **Cache:** **SQLite** via Python's built-in `sqlite3` (no ORM, no extra dependency — plain SQL in a small data-access module).
- **Packaging (Linux):** Flatpak as the primary distribution; also runnable directly via `python -m musicplayer` for development. RPM is a nice-to-have.
- **License:** GPL-3.0 (matches the lineage of these players and Bill's open-source intent). Put a real `LICENSE` file in the repo.

**Explicitly rejected:** Rust (steeper, thinner audio bindings, overkill for a folder-reading app), Electron/web stack (heavy, non-native), React/Angular, any ORM, any cloud/streaming dependency.

**Dependencies list (keep it short):**
`PyGObject (gi)`, `GTK4`, `Libadwaita`, `GStreamer (+ good/bad/ugly plugin sets for codecs)`, `mutagen`. SQLite is stdlib.

---

## 4. Supported formats (v1)
MUST decode and read tags for: **FLAC, MP3, OGG Vorbis, Opus, M4A/AAC (ALAC + AAC), WAV**.
SHOULD display embedded cover art from any of these. If a folder has a `cover.jpg`/`folder.jpg`/`front.png`, use it as a fallback when no embedded art exists.

---

## 5. Library model & scanning
- On first run, the user picks one or more **music root folders**. Store these paths in a small config file (`~/.config/musicplayer/config.toml` on Linux; use the platform config dir elsewhere).
- A **scanner** walks the roots recursively, reads each audio file's tags via mutagen, and writes a row per track into the SQLite cache. The scan MUST run on a background thread and show an **obvious progress indicator** (count + a bar). Onboarding is a named priority — see §9.
- **Incremental rescan:** on later launches, compare file modification times / paths against the cache and only re-read changed or new files. A manual "Rescan library" action MUST exist.
- The app reads from the cache for all browsing/search; it only touches the original files to (a) read art it didn't cache and (b) play audio.

### Cache schema (minimum)
A single SQLite file at `~/.local/share/musicplayer/library.db`. Suggested tables/columns (builder may refine, but keep it this simple):

- `tracks`: `id, file_path, title, artist, album_artist, album, disc_number, track_number, year, genre, duration_seconds, file_mtime, has_embedded_art`
- `albums` (derived/materialized for speed): `id, album_title, album_artist, year, cover_image_path_or_blobref, track_count`
- A small `meta` table: `schema_version`, `last_scan_at`.

Cover art: cache thumbnails to disk under `~/.cache/musicplayer/art/` keyed by album id; never store originals back into the user's files.

---

## 6. The "folder vs tags" rule (critical — read carefully)
Goal: group tracks into albums correctly even when folder layout and tags disagree.

**Hierarchy of trust when grouping a track into an album:**
1. **Embedded tags win.** Group by `ALBUM` + `ALBUMARTIST` (fall back to `ARTIST` if `ALBUMARTIST` is blank). Use `MUSICBRAINZ_ALBUMID` if present as the strongest possible album key.
2. **Folder is a fallback only.** If `ALBUM` is missing/blank, infer the album name from the containing folder's name, and the album-artist from the parent folder's name (`Artist/Album/track.flac`).
3. **A folder is NOT required to be an album.** Treat "one folder = one album" as a *strong default for fallback*, never a hard rule. Multiple albums in one folder (loose files, compilations) MUST still resolve correctly via their tags. One album spanning `Disc 1/` + `Disc 2/` subfolders MUST merge into a single album via matching `ALBUM` tag + `DISCNUMBER`.
4. **Never auto-"fix" a mismatch by editing files.** If tags and folder disagree, trust the tags silently and move on. (A later, optional UI could *surface* mismatches for the user to review — but the app never changes files on its own.)

This rule directly answers the open design question: do not assume or require folder == album; assume tags, use the folder only to fill gaps.

---

## 7. Primary UI (search-first + album art)
Single main window, GTK4/Libadwaita, with three persistent zones:

**a) Top: the search bar.** Always reachable (focused on `Ctrl+F` and on launch). One box, instant/as-you-type filtering across track title, artist, album, album-artist. Results update live. This is the primary way to navigate — make it fast and prominent. (Note: existing players often *lack* good song search; this is our edge — get it right.)

**b) Center: the results / browse area.** Two display modes the user can toggle:
   - **Album-art grid** (default): a grid of album covers with title + artist beneath. Clicking an album opens its track list. This satisfies "I want to see album art."
   - **Flat track list** (when searching): search results appear as a clean list of `Title — Artist — Album` rows with the album thumbnail at left. Enter or double-click plays; an obvious "add to queue" affordance per row.
   Scrolling MUST stay smooth through thousands of items (use list virtualization / GTK's model-backed list views).

**c) Bottom: the now-playing bar.** Current track's cover art (small), title/artist, a **scrubber the user can click AND drag** (do not require scroll-wheel for seek or volume — that was a named complaint about Euphonica), play/pause/next/prev, a clickable+draggable **volume slider**, and the mascot's home perch (see §8).

**Queue:** a slide-out or side panel showing the play queue. Queue items SHOULD be **drag-and-drop reorderable** (not button-only). When whole albums are queued, group them visually as units (a praised Recordbox behavior).

**Aesthetic — monospace / console:** Use a **monospace font** (`var` — ship/depend on a common one like JetBrains Mono, Iosevka, or fall back to the system monospace) for track listings, search, and chrome text. The vibe is a clean terminal/console, *not* a spreadsheet and *not* skeuomorphic. Album art provides the color and warmth; the text furniture is mono and calm. Keep it readable: no font below 12px.

---

## 8. The mascot (the soul of the app) — "The Deck"
A small **8/16-bit pixel-art reel-to-reel tape deck** that lives inside the interface and is animated by player state. Inspired by vintage blue Technics/Akai reel-to-reel decks — a *machine with a face*, in the friendly spirit of the Claude Code pixel character but its own creature. **Full art brief in `MASCOT.md`.** This is a first-class feature, not a gimmick to bolt on later.

Requirements:
- **The two reels are its eyes** and MUST sit **up high, rising above the top edge of the body** (the signature reel-to-reel silhouette). The **VU meters are eyebrows** (needles bounce with the music); a **transport button is the mouth**.
- **Lives in the now-playing bar** by default. Because it's a deck, it leans toward *perch-and-react* rather than walking; it MAY drift along the bottom edge.
- **State-driven animations**, at minimum:
  - *Idle / paused:* reels still, needles resting, mouth flat; occasional slow blink or "Zzz".
  - *Playing:* reels **spin**, VU needles **bounce**, VU faces glow amber, mouth smiles (simple loop fine; beat-sync is a future MAY).
  - *Searching / scanning:* reels **squint**, threading/"..." motion, effortful mouth.
  - *Track change:* brief reaction (quick spin-up / hop).
- SHOULD recolor to match the active theme (§8b).
- **Implementation:** sprite-sheet PNGs (16×16 or 32×32 frames, integer-scaled up so pixels stay crisp — nearest-neighbor scaling, never blurred). Drive frames on a simple timer keyed to player state. Keep the animation system tiny and data-driven (a small JSON describing states → frame ranges → frame durations) so new animations can be added without touching core code.
- **Respectful:** the mascot MUST be mutable/disable-able in settings for people who don't want it. Default on.
- Art can start as placeholder programmer-pixel-art; the spec just needs the *system* in place so real sprites drop in later.

---

## 8b. Theming (the app is themable)
The console aesthetic invites palettes, so theming is a first-class feature, not an afterthought.
- Ship a small set of built-in **themes** (e.g. a default light, a dark/console-green, a warm amber-CRT, a high-contrast). Each theme is a **plain text file** (TOML or CSS — prefer a small named-color TOML the app maps onto GTK CSS) defining: background, surface, text, accent, the monospace font choice, and a few mascot-friendly accent colors.
- Themes live in a folder the user can open: `~/.config/musicplayer/themes/`. Dropping a new `.toml` theme file in there MUST make it appear in the theme picker — same open, plain-files spirit as the notes (see §8c).
- Theme selection lives in Settings; switching applies live without restart.
- Keep it simple: a theme is just colors + font, mapped to GTK4 CSS variables. No scripting, no per-widget skinning in v1.

## 8c. Notes (plain-text, Obsidian-style, per artist / album / song)
The user can write a free-form note attached to an **artist, an album, or a single song**. This is a first-class feature.

**Where notes live (the important part):**
- Notes are **plain Markdown (`.md`) files on disk** — never written into the music files' tags, and never stored *in* the SQLite database. They are the user's own data, fully portable, drag-and-droppable elsewhere (the Obsidian philosophy). The plain files ARE the export; there is no "export" step to remember and no lock-in.
- **Default location: `~/Music Notes/`** — a visible, obvious folder in the user's home directory, sitting alongside their `Music` folder, openable in Obsidian or any text editor, backed up like any normal folder. (Deliberately NOT a hidden `~/.local/share/...` path — these are writings the user cares about, not app internals.) The path is shown and changeable in Settings.
- The app reads and writes only inside this notes folder — it still NEVER touches the user's music files (§2 holds).
- **Indexing for search is fine, storage is not:** the app MAY record in the SQLite *cache* that a note exists (and even cache note body text for fast full-text search), but the `.md` files remain the single source of truth. Deleting the cache re-reads the notes folder; it never loses a note.
- **File naming** encodes what the note is about, human-readably:
  - Song note: `Artist - Album - Song.md`
  - Album note: `Artist - Album.md`
  - Artist note: `Artist.md`
  - Sanitize illegal filename characters (`/`, etc.) but keep names readable. If two things collide, disambiguate minimally (e.g. append a short year or id), but prefer the clean name.
- **File contents:** a small YAML front-matter block + the user's Markdown body. Front-matter MUST include: `type` (artist|album|song), `artist`, `album` (if applicable), `song` (if applicable), `created` (ISO 8601 timestamp), `updated` (ISO 8601 timestamp). The body below is free Markdown. Example:
  ```
  ---
  type: song
  artist: David Bowie
  album: Low
  song: Sound and Vision
  created: 2026-06-12T14:03:00-04:00
  updated: 2026-06-12T14:03:00-04:00
  ---
  Best two minutes of the record. The way the vocal doesn't come in until halfway.
  ```
- **In the UI:** a small "note" affordance (pencil/note icon) on each artist, album, and song. Clicking opens a simple Markdown text editor pane. Saving writes/updates the corresponding `.md` file and stamps `updated`. An indicator shows when an item already has a note. Notes are searchable in v1 only by their existence (a future MAY: full-text search across note bodies).
- The notes folder is **not** the disposable cache — deleting the cache must never delete notes. Notes are real, backed-up user data.

## 9. Onboarding (a named priority)
Make first-run painless — this is explicitly where many competitors fail:
1. Launch → one clear screen: "Choose your music folder" with one prominent button.
2. User picks a folder → an obvious progress bar fills as the scan runs.
3. Done → drop straight into the album-art grid with the mascot waving.
No server setup, no config files to hand-edit, no hidden steps.

---

## 10. Desktop integration (v1 SHOULD)
- Expose **MPRIS** (the Linux media-player D-Bus interface) so the track shows in the GNOME shell / lock screen and responds to media keys (play/pause/next/prev). GStreamer + a small MPRIS module covers this.
- Remember window size and last view between launches.
- Restore the previous queue/now-playing on relaunch (Amberol does this; it's a small, loved touch).

---

## 11. Explicit non-goals for v1 (keep scope tight)
- No streaming services, no network sources (no Jellyfin/Subsonic/Spotify). Local files only.
- No writing/editing of the user's tags or music files. (Writing plain-text *notes* into the app's own notes folder is allowed and expected — see §8c — but the user's music files are never touched.)
- No internet metadata fetching in v1 (cover-art download, lyrics, artist photos are all **future MAY**).
- No smart playlists / recommendation engine in v1 (future MAY).
- No phone/mobile build.

---

## 12. Suggested build order (for the implementer)
1. Project skeleton: Python package, GTK4 window that opens, dependency check.
2. Config + folder picker (onboarding screen).
3. Scanner: walk folders, read tags via mutagen, write to SQLite, with a background thread + progress bar.
4. Album grid view reading from the cache; click-through to track list.
5. GStreamer playback: play/pause/seek/next/prev, gapless, now-playing bar with click+drag scrubber and volume.
6. Search bar with live filtering across the cache.
7. Queue panel with drag-and-drop reorder; album grouping in the queue.
8. The mascot system: sprite renderer + state machine + the core animation set.
9. Theming: load plain-text theme files → GTK CSS, live theme switcher (§8b).
10. Notes: plain-`.md` notes per artist/album/song with the editor pane and note indicators (§8c).
11. MPRIS + media keys + restore-last-session.
12. Settings (choose music folders, rescan, toggle mascot, pick monospace font, pick theme, set notes folder).
13. Flatpak packaging + `LICENSE` (GPL-3.0) + README.

---

## 13. Acceptance checks (how we know it's right)
- Point it at a folder of a few thousand mixed-format tracks → scans with visible progress, then browses smoothly.
- Delete `library.db` → relaunch rebuilds cleanly, nothing lost from the user's files (verify file mtimes/contents unchanged).
- An album whose tags disagree with its folder name groups by the **tag**, not the folder.
- A two-disc album split across `Disc 1/`/`Disc 2/` shows as **one** album.
- `Ctrl+F`, type three letters of a song → it appears and plays on Enter.
- Scrubber and volume both work by **click and drag** (not just scroll).
- The mascot visibly changes behavior between paused, playing, and scanning — and can be turned off in settings.
- The app never modifies any file under the user's music roots (diff a copy before/after a full session).
- Writing a note on a song creates a readable `Artist - Album - Song.md` file in the notes folder with correct front-matter and timestamps; the file opens fine in any text editor and survives a cache rebuild.
- Switching themes changes the look live without restart; dropping a new theme `.toml` into the themes folder makes it appear in the picker.
