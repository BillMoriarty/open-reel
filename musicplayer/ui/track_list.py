import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Adw, Gdk, Pango, GObject
import mutagen


def _fmt(seconds):
    if not seconds:
        return '--:--'
    m, s = divmod(int(seconds), 60)
    return f'{m}:{s:02d}'


class TrackRow(Gtk.ListBoxRow):

    def __init__(self, track_row):
        super().__init__()
        self.file_path = track_row['file_path']
        self.title     = track_row['title'] or 'Unknown Track'
        self.artist    = (track_row['artist'] or
                          track_row['album_artist'] or 'Unknown Artist')

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(16)
        box.set_margin_end(16)

        num = track_row['track_number'] or 0
        num_lbl = Gtk.Label(label=f'{num:02d}' if num else '--')
        num_lbl.add_css_class('track-number')
        num_lbl.set_width_chars(4)
        num_lbl.set_halign(Gtk.Align.END)
        box.append(num_lbl)

        title_lbl = Gtk.Label(label=self.title)
        title_lbl.add_css_class('track-title')
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_hexpand(True)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(title_lbl)

        dur_lbl = Gtk.Label(label=_fmt(track_row['duration_seconds']))
        dur_lbl.add_css_class('track-duration')
        dur_lbl.set_halign(Gtk.Align.END)
        box.append(dur_lbl)

        self.set_child(box)

        gesture = Gtk.GestureClick()
        gesture.set_button(3)
        gesture.connect('pressed', self._on_right_click)
        self.add_controller(gesture)

    def _on_right_click(self, gesture, _n, x, y):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        popover = Gtk.Popover()
        popover.set_has_arrow(False)
        popover.set_parent(self)

        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        popover.set_pointing_to(rect)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        show_btn = Gtk.Button(label='Show in Files')
        show_btn.add_css_class('flat')
        show_btn.set_halign(Gtk.Align.FILL)
        show_btn.connect('clicked', lambda _: (popover.popdown(), self._show_in_files()))
        box.append(show_btn)

        info_btn = Gtk.Button(label='File info')
        info_btn.add_css_class('flat')
        info_btn.set_halign(Gtk.Align.FILL)
        info_btn.connect('clicked', lambda _: (popover.popdown(), self._show_file_info()))
        box.append(info_btn)

        popover.set_child(box)
        popover.popup()

    def _show_in_files(self):
        folder = str(Path(self.file_path).parent)
        subprocess.Popen(['xdg-open', folder])

    def _show_file_info(self):
        info = _read_file_info(self.file_path)
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=self.title,
            body=info,
        )
        dialog.add_response('close', 'Close')
        dialog.set_default_response('close')
        dialog.present()


def _read_file_info(file_path):
    path = Path(file_path)
    try:
        size = path.stat().st_size
        size_str = f'{size / 1048576:.1f} MB' if size > 1048576 else f'{size / 1024:.0f} KB'
    except OSError:
        size_str = 'unknown'

    fmt_map = {
        '.flac': 'FLAC', '.mp3': 'MP3', '.m4a': 'AAC (M4A)',
        '.aac': 'AAC', '.ogg': 'Ogg Vorbis', '.opus': 'Opus',
        '.wav': 'WAV', '.mp4': 'AAC (MP4)',
    }
    fmt = fmt_map.get(path.suffix.lower(), path.suffix.upper().lstrip('.'))

    lines = [f'Format:      {fmt}', f'Size:        {size_str}', f'Path:        {file_path}']

    try:
        audio = mutagen.File(file_path)
        if audio and hasattr(audio, 'info'):
            inf = audio.info
            dur = getattr(inf, 'length', 0)
            if dur:
                m, s = divmod(int(dur), 60)
                lines.insert(0, f'Duration:    {m}:{s:02d}')
            sr = getattr(inf, 'sample_rate', 0)
            if sr:
                lines.append(f'Sample rate: {sr / 1000:.1f} kHz')
            bps = getattr(inf, 'bits_per_sample', 0)
            if bps:
                lines.append(f'Bit depth:   {bps}-bit')
            br = getattr(inf, 'bitrate', 0)
            if br:
                lines.append(f'Bitrate:     {br // 1000} kbps')
            ch = getattr(inf, 'channels', 0)
            if ch:
                lines.append(f'Channels:    {"Stereo" if ch == 2 else "Mono" if ch == 1 else str(ch)}')
    except Exception:
        pass

    return '\n'.join(lines)


class TrackListPage(Adw.NavigationPage):

    __gsignals__ = {
        'track-activated': (GObject.SignalFlags.RUN_LAST, None, (str, str, str)),
    }

    def __init__(self, album_title, album_artist, tracks):
        super().__init__(title=album_title)
        self._tracks       = tracks
        self._playing_row  = None
        self._build_ui(album_title, album_artist, tracks)

    def _build_ui(self, album_title, album_artist, tracks):
        # No per-page HeaderBar -- the window owns the header bar.
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_hexpand(True)
        content.set_vexpand(True)

        # Album info strip
        strip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        strip.set_margin_start(16)
        strip.set_margin_end(16)
        strip.set_margin_top(12)
        strip.set_margin_bottom(12)

        al = Gtk.Label(label=album_title)
        al.add_css_class('album-title')
        al.set_halign(Gtk.Align.START)
        al.set_ellipsize(Pango.EllipsizeMode.END)
        strip.append(al)

        ar = Gtk.Label(label=album_artist)
        ar.add_css_class('album-artist')
        ar.set_halign(Gtk.Align.START)
        strip.append(ar)

        cnt = Gtk.Label(
            label=f'{len(tracks)} track{"s" if len(tracks) != 1 else ""}'
        )
        cnt.add_css_class('onboarding-note')
        cnt.set_halign(Gtk.Align.START)
        strip.append(cnt)

        content.append(strip)
        content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Track list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listbox = Gtk.ListBox()
        self._listbox.add_css_class('track-listbox')
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.set_activate_on_single_click(True)
        self._listbox.connect('row-activated', self._on_row_activated)

        for track in tracks:
            self._listbox.append(TrackRow(track))

        scrolled.set_child(self._listbox)
        content.append(scrolled)

        self.set_child(content)

    def highlight_track(self, file_path):
        """Mark the playing track bold+blue; clear the previous playing row."""
        if self._playing_row:
            self._playing_row.remove_css_class('track-playing')
            self._playing_row = None

        row = self._listbox.get_first_child()
        while row:
            if isinstance(row, TrackRow) and row.file_path == file_path:
                row.add_css_class('track-playing')
                self._listbox.select_row(row)
                self._playing_row = row
                break
            row = row.get_next_sibling()

    def _on_row_activated(self, _lb, row):
        self.emit('track-activated', row.file_path, row.title, row.artist)
