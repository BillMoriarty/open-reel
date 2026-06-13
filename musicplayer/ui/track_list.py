import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Adw, Pango, GObject


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
