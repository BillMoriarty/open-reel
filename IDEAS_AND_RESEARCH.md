# Fedora Music Player — Ideas & Research

*An open-source / shareware local-file music player for Fedora (cross-platform welcome). Working notes started June 12, 2026.*

---

## 1. The idea
A local-file music player that runs on Fedora. Other platforms fine if they come for free. Open source or shareware. The library is files Bill owns (ripped FLACs, Bandcamp downloads, etc.), not a streaming service.

This fits the "own your media" movement: ditching Spotify, ripping CDs to FLAC, supporting artists directly via Bandcamp/iTunes/CD.

---

## 2. Layout ideas

The conventional layout is three columns: **artist → album → song**, left to right. It mirrors a shelved record collection and the eye flows broad-to-narrow. Safe and proven, but it assumes clean metadata, spends lots of screen on names instead of cover art, and rewards browsing over fast finding.

Three alternatives that also make sense, each for a different listener:

**A. Sidebar + album-art grid** — slim sidebar to pick a view (Albums / Artists / Songs / Playlists); main area fills with cover art. How Spotify, Apple Music, and Lollypop work. The eye recognizes a cover faster than a name, and it forgives messy metadata. Probably what most modern listeners now expect.

**B. Single search-driven list** — no columns; just a search box and one flat list (like cmus, Tauon, or a command palette). Premise: past a few hundred albums nobody browses three columns — they type "bowie low" and hit the track. Fastest path to sound, simplest to build, suits a power user with a large well-tagged library. (Good fit for Bill's lightweight/long-lasting taste.)

**C. Now-playing centric** — big current-album art with the queue beside it; library is secondary. The "play a record and watch it spin" layout (Amberol's philosophy). Lovely for casual listening, weaker for managing a big collection.

**Takeaway:** the three views answer different questions — three-column = *navigate a known structure*, grid = *recognize by sight*, search = *retrieve a known track*. The right pick depends on whether the target listener browses, recognizes, or retrieves. The best players offer a couple of views and let the listener choose.

---

## 3. Forkability notes
Most candidates are open source and forkable. Watch the license:
- **Copyleft (GPL):** fork freely, but the fork must stay open under GPL. Covers most (Rhythmbox, Clementine, Strawberry, Sayonara, Quod Libet, Lollypop, Elisa, Audacious, DeaDBeeF, Amarok, Exaile, Pragha, Gmusicbrowser, cmus, ncmpcpp, Amberol, VLC).
- **Permissive (BSD/MIT):** fork freely, may even close source (e.g. musikcube, BSD).
- Strawberry was forked from Clementine, forked from Amarok — a proven fork lineage.
- Cleanest forks build on one modern toolkit + an existing media backend (GStreamer). Most hackable for Bill's taste: **Quod Libet** (Python + GTK, readable) or **Strawberry/Clementine** (C++/Qt, mature). Smallest codebases to fully understand: **cmus**, **musikcube**.
- Always check the actual `LICENSE` file in the repo before committing.

---

## 4. Reference: crescentrose blog — "The state of Linux music players in 2026"
Source: https://crescentro.se/posts/linux-music-players-2026/ (Jan 26, 2026). Lobste.rs thread: https://lobste.rs/s/bpqtph/state_linux_music_players_2026

Author's criteria (a useful spec for our own app): modern desktop-native UI (not a blown-up phone app, not a spreadsheet, no CLI); respects protocols (background play, keyboard shortcuts, shows up as a media player in the shell); snappy with a moderately sized library; real "music library" concept, fast quality search, easy playlists/queues, **respects existing metadata and doesn't rewrite your files**.

Author's reviews:

- **Amberol** (gitlab.gnome.org/World/amberol) — small, simple, GNOME-integrated. No library management beyond restoring last playlist. Waveform scrubber is a nice touch. Great for casual listening / default file-open app.
- **Euphonica** (github.com/htkhiem/euphonica) — MPD client; needs MPD set up. Author's former daily driver. Prettiest in the list ("glowing" UI, generous album art, tasteful background visualizer), synced lyrics. Quirks: chokes on large collections, no song search, queue reorder by buttons not drag-and-drop, volume only via scroll wheel.
- **Feishin** (github.com/jeffvli/feishin) — self-hosted; needs Jellyfin/Navidrome/Subsonic. Most feature-complete; the "personal Spotify." Command palette, recommendations, highlights, stats. Downsides: Electron app (web-isms, spinners, another Chrome instance, Electron audio stack). Author's top pick if you have a server.
- **Lollypop** (gitlab.gnome.org/World/lollypop) — "album of the day," opens on suggestions not an A-Z list, YouTube Music playback. But painful UX: confusing onboarding, hidden sidebar on resize, obscure add-directory button, hidden queue. "Bad GNOME-isms."
- **Plattenalbum** (github.com/SoongNoonien/plattenalbum) — album-focused MPD client; Amberol + basic search. Clean and minimal but little customization, can't list/sort all albums well, no multi-disc support. Like the Longplay iOS/Mac app in spirit; lots of potential.
- **Recordbox** (codeberg.org/edestcroix/Recordbox) — GTK/Libadwaita. **Best onboarding of the bunch**; comfortable three-pane iTunes-style library; Ctrl+F universal search; snappy scrolling through hundreds of albums; multi-disc support; albums grouped & reorderable in the queue as units. Minor: unfinished "now playing," some settings split awkwardly. Impressive for a pre-1.0, ~2 years of work.
- **Strawberry / Clementine / Amarok** — Amarok was *the* player of its day; influenced Clementine and Strawberry. All look like a late-90s/early-2010s UI. Strawberry is the most prominent and slightly better (context pane, more consistent). Less intuitive than ideal, giant translucent strawberry watermark. Solid foundation; author thinks the lineage could reclaim the crown with a clean modern redesign.
- **Tauon** (github.com/Taiko2k/Tauon) — "everything-is-a-playlist" power-user player; native and very snappy (smooth through 8k+ tracks). Supports Plex/Subsonic/Jellyfin/Spotify as network sources; tag management, lyrics editor, Discord integration. The Linux foobar2000. Quirks: DJ-deck look, scroll bar on the left, learning curve.
- **fooyin** (fooyin.org) — added in an update; the most-requested foobar2000-style player from the comments. Author hadn't tested but it comes highly recommended.

Author's summary: have a server → **Feishin**; local/Electron-averse power user → **Tauon**; otherwise **Recordbox** is shaping up nicely; already running MPD → **Euphonica**; just a few tracks → **Amberol**.

---

## 5. Where the gap is (opportunity for our app)
The crowded paths are simple GNOME players (Amberol, Rhythmbox) and heavy library managers. Where listeners still grumble — and where a newcomer could be welcomed:
- Clean, lightweight **library management** without bloat.
- Fast **tag editing**.
- **Gapless local playback** without a heavy stack.
- A genuinely good **search-first** experience (Recordbox's Ctrl+F is praised; Euphonica notably *lacks* song search).
- Modern desktop-native UI that doesn't rewrite your files (the recurring wish across every review).

Recordbox + Euphonica show the bar for native GTK; the unmet need is one that nails onboarding, search, metadata-respect, and gapless playback in a light package.
