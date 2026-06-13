# Music Player

A native GTK4 music player for Fedora / GNOME, built with Python and Libadwaita. No Electron, no web runtime -- just a clean desktop app that reads your local music folders and stays out of the way.

![screenshot](screenshots/main.png)

## Features

- Album grid with cover art (embedded tags or folder image)
- Click an album to see the track list; click a track to play
- Now-playing bar with scrubber, time, shuffle, repeat, and volume
- Repeat modes: off / album / track (with "1" badge)
- Shuffle within an album (Fisher-Yates)
- Library / Recent / Top Played tabs above the grid
- Per-album and per-track notes saved as plain `.md` files
- Animated mascot "The Deck" -- reel-to-reel with eye tracking, spinning reels, and stereo VU bars
- 4 built-in themes: Technics Blue (default), Phosphor Green, Warm Amber, Daylight
- Live theme switching with no restart
- MPRIS2 support -- media keys, GNOME shell now-playing, lock screen controls
- Desktop launcher (`.desktop` file + shell wrapper)
- Keyboard shortcuts: `Ctrl+Q` / `Ctrl+W` to quit

## Requirements

All dependencies are system packages -- no pip install needed.

```
python3
python3-gobject        (PyGObject / GTK4 bindings)
python3-gst-1.0        (GStreamer Python bindings)
python3-mutagen        (audio tag reading)
python3-dbus           (MPRIS2 / media keys)
gstreamer1-plugins-good
gstreamer1-plugins-bad-free
libadwaita
```

On Fedora:

```bash
sudo dnf install python3-gobject python3-gst1 python3-mutagen \
                 python3-dbus gstreamer1-plugins-good \
                 gstreamer1-plugins-bad-free libadwaita
```

## Running

```bash
git clone <repo-url>
cd music-player
python run.py
```

On first launch you will be prompted to choose a music folder. The app scans it in the background and is ready in seconds.

## Desktop launcher (optional)

Create `~/.local/bin/musicplayer`:

```bash
#!/bin/bash
exec python3 /path/to/music-player/run.py "$@"
```

Create `~/.local/share/applications/musicplayer.desktop`:

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Music Player
Exec=musicplayer
Icon=multimedia-player
Terminal=false
Categories=Audio;Music;Player;
StartupWMClass=musicplayer
```

Then:

```bash
chmod +x ~/.local/bin/musicplayer
update-desktop-database ~/.local/share/applications/
```

## Data locations

| What | Where |
|---|---|
| Library database | `~/.local/share/musicplayer/library.db` |
| Notes | `~/.local/share/musicplayer/notes/` |
| Config | `~/.config/musicplayer/config.toml` |

The app never touches your music files. No renaming, no moving, no tag writing.

## Themes

Open the preferences dialog (gear icon) to switch themes. The change is instant and persists across restarts.

| Theme | Style |
|---|---|
| Technics Blue | Dark -- deep navy, warm cream text, Technics blue accents |
| Phosphor Green | Dark -- terminal green on near-black |
| Warm Amber | Dark -- amber on dark brown |
| Daylight | Light -- warm off-white with blue accents |

## License

MIT
