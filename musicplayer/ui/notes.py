from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango, GLib
from musicplayer.database import DATA_DIR

NOTES_DIR = DATA_DIR / 'notes'


class _NoteSection(Gtk.Box):
    """One note section: header + overlay text area with placeholder."""

    def __init__(self, section_label: str, placeholder: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._save_timer  = None
        self._path        = None
        self._switching   = False

        # ---- Header block -----------------------------------------------
        # Outer row: labels left, optional art thumbnail right
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_row.set_margin_start(12)
        header_row.set_margin_end(10)
        header_row.set_margin_top(8)
        header_row.set_margin_bottom(6)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.set_hexpand(True)
        header.set_valign(Gtk.Align.CENTER)

        # Row 1: section title + content dot + undo/redo buttons
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self._section_lbl = Gtk.Label(label=section_label)
        self._section_lbl.add_css_class('notes-section-title')
        self._section_lbl.set_halign(Gtk.Align.START)
        title_row.append(self._section_lbl)

        self._dot = Gtk.Label(label='●')
        self._dot.add_css_class('note-has-content')
        self._dot.set_visible(False)
        title_row.append(self._dot)

        _spacer = Gtk.Box()
        _spacer.set_hexpand(True)
        title_row.append(_spacer)

        self._undo_btn = Gtk.Button()
        self._undo_btn.set_icon_name('edit-undo-symbolic')
        self._undo_btn.add_css_class('flat')
        self._undo_btn.add_css_class('note-edit-btn')
        self._undo_btn.set_tooltip_text('Undo (Ctrl+Z)')
        self._undo_btn.set_sensitive(False)
        self._undo_btn.connect('clicked', self._on_undo_clicked)
        title_row.append(self._undo_btn)

        self._redo_btn = Gtk.Button()
        self._redo_btn.set_icon_name('edit-redo-symbolic')
        self._redo_btn.add_css_class('flat')
        self._redo_btn.add_css_class('note-edit-btn')
        self._redo_btn.set_tooltip_text('Redo (Ctrl+Shift+Z)')
        self._redo_btn.set_sensitive(False)
        self._redo_btn.connect('clicked', self._on_redo_clicked)
        title_row.append(self._redo_btn)

        header.append(title_row)

        # Row 2: primary context (artist or track title)
        self._ctx1_lbl = Gtk.Label(label='')
        self._ctx1_lbl.add_css_class('notes-context')
        self._ctx1_lbl.set_halign(Gtk.Align.START)
        self._ctx1_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._ctx1_lbl.set_visible(False)
        header.append(self._ctx1_lbl)

        # Row 3: secondary context (album title)
        self._ctx2_lbl = Gtk.Label(label='')
        self._ctx2_lbl.add_css_class('notes-context-sub')
        self._ctx2_lbl.set_halign(Gtk.Align.START)
        self._ctx2_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._ctx2_lbl.set_visible(False)
        header.append(self._ctx2_lbl)

        header_row.append(header)

        # Small art thumbnail (right side, album section only)
        art_box = Gtk.Box()
        art_box.set_size_request(56, 56)
        art_box.set_halign(Gtk.Align.END)
        art_box.set_valign(Gtk.Align.CENTER)
        art_box.set_overflow(Gtk.Overflow.HIDDEN)
        art_box.add_css_class('notes-art-thumb')
        art_box.set_visible(False)

        self._art_picture = Gtk.Picture()
        self._art_picture.set_content_fit(Gtk.ContentFit.COVER)
        self._art_picture.set_hexpand(True)
        self._art_picture.set_vexpand(True)
        art_box.append(self._art_picture)

        self._art_box = art_box
        header_row.append(self._art_box)

        self.append(header_row)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ---- Text area with overlay placeholder -------------------------
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._tv = Gtk.TextView()
        self._tv.add_css_class('notes-text')
        self._tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._tv.set_left_margin(12)
        self._tv.set_right_margin(12)
        self._tv.set_top_margin(10)
        self._tv.set_bottom_margin(10)
        buf = self._tv.get_buffer()
        buf.set_enable_undo(True)
        buf.connect('changed', self._on_changed)
        buf.connect('notify::can-undo', self._on_undo_state_changed)
        buf.connect('notify::can-redo', self._on_undo_state_changed)
        scrolled.set_child(self._tv)

        overlay = Gtk.Overlay()
        overlay.set_child(scrolled)

        self._placeholder = Gtk.Label(label=placeholder)
        self._placeholder.add_css_class('notes-placeholder')
        self._placeholder.set_halign(Gtk.Align.START)
        self._placeholder.set_valign(Gtk.Align.START)
        self._placeholder.set_margin_start(14)
        self._placeholder.set_margin_top(12)
        self._placeholder.set_sensitive(False)
        overlay.add_overlay(self._placeholder)

        self.append(overlay)

    # ------------------------------------------------------------------ #
    # public API

    def load(self, path, ctx1: str = '', ctx2: str = '', art_path: str = None):
        """Load note from path. ctx1 = first context line, ctx2 = second."""
        self._flush()
        self._path = path
        self._set_context(ctx1, ctx2)
        if art_path:
            try:
                self._art_picture.set_filename(art_path)
                self._art_box.set_visible(True)
            except Exception:
                self._art_box.set_visible(False)
        else:
            self._art_box.set_visible(False)
        text = ''
        if path and path.exists():
            try:
                text = path.read_text(encoding='utf-8')
            except OSError:
                pass
        self._switching = True
        buf = self._tv.get_buffer()
        buf.set_enable_undo(False)   # clears history before loading new note
        buf.set_text(text)
        buf.place_cursor(buf.get_start_iter())
        buf.set_enable_undo(True)
        self._switching = False
        self._update_indicators(text)

    def clear(self, ctx1: str = '', ctx2: str = ''):
        """Show empty / non-editable state."""
        self._flush()
        self._path = None
        self._set_context(ctx1, ctx2)
        self._art_box.set_visible(False)
        self._switching = True
        buf = self._tv.get_buffer()
        buf.set_enable_undo(False)
        buf.set_text('')
        buf.set_enable_undo(True)
        self._switching = False
        self._update_indicators('')
        self._tv.set_editable(False)
        self._placeholder.set_visible(True)

    def flush(self):
        self._flush()

    def reload(self):
        """Re-read from disk if the file changed externally."""
        if self._path is None:
            return
        text = ''
        if self._path.exists():
            try:
                text = self._path.read_text(encoding='utf-8')
            except OSError:
                pass
        buf = self._tv.get_buffer()
        s, e = buf.get_bounds()
        if buf.get_text(s, e, False) == text:
            return
        self._switching = True
        buf.set_enable_undo(False)
        buf.set_text(text)
        buf.place_cursor(buf.get_start_iter())
        buf.set_enable_undo(True)
        self._switching = False
        self._update_indicators(text)

    @property
    def text_view(self):
        return self._tv

    # ------------------------------------------------------------------ #

    def _on_undo_clicked(self, _btn):
        self._tv.get_buffer().undo()
        self._tv.grab_focus()

    def _on_redo_clicked(self, _btn):
        self._tv.get_buffer().redo()
        self._tv.grab_focus()

    def _on_undo_state_changed(self, buf, _pspec):
        self._undo_btn.set_sensitive(buf.get_can_undo())
        self._redo_btn.set_sensitive(buf.get_can_redo())

    def _set_context(self, ctx1: str, ctx2: str):
        for lbl, text in ((self._ctx1_lbl, ctx1), (self._ctx2_lbl, ctx2)):
            lbl.set_text(text)
            lbl.set_visible(bool(text))

    def _on_changed(self, buf):
        if self._switching:
            return
        self._update_placeholder_visibility()
        s, e = buf.get_bounds()
        self._dot.set_visible(bool(buf.get_text(s, e, False).strip()))
        if self._save_timer:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add(1500, self._auto_save)

    def _auto_save(self):
        self._flush()
        return GLib.SOURCE_REMOVE

    def _flush(self):
        if self._save_timer:
            GLib.source_remove(self._save_timer)
            self._save_timer = None
        if not self._path:
            return
        buf  = self._tv.get_buffer()
        s, e = buf.get_bounds()
        text = buf.get_text(s, e, False)
        if text.strip():
            try:
                self._path.write_text(text, encoding='utf-8')
            except OSError:
                pass
        elif self._path.exists():
            try:
                self._path.unlink()
            except OSError:
                pass

    def _update_indicators(self, text):
        self._dot.set_visible(bool(text.strip()))
        self._tv.set_editable(bool(self._path))
        self._update_placeholder_visibility()

    def _update_placeholder_visibility(self):
        buf  = self._tv.get_buffer()
        s, e = buf.get_bounds()
        self._placeholder.set_visible(not buf.get_text(s, e, False))


class NotesPane(Gtk.Box):
    """Right-side notes pane: album note (top) and track note (bottom)."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        NOTES_DIR.mkdir(parents=True, exist_ok=True)

        self._album_artist = ''
        self._album_title  = ''
        self._track_title  = ''

        self._build_ui()
        self.connect('map', self._on_mapped)

    # ------------------------------------------------------------------ #

    def _build_ui(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.set_vexpand(True)
        paned.set_hexpand(True)
        paned.set_wide_handle(True)
        paned.set_position(240)

        self._album_section = _NoteSection(
            'album note',
            'write thoughts about this album...',
        )
        paned.set_start_child(self._album_section)
        paned.set_resize_start_child(True)
        paned.set_shrink_start_child(True)

        self._track_section = _NoteSection(
            'track note',
            'play a track to write a note about it...',
        )
        self._track_section.clear()
        paned.set_end_child(self._track_section)
        paned.set_resize_end_child(True)
        paned.set_shrink_end_child(True)

        self.append(paned)

    # ------------------------------------------------------------------ #
    # public API

    def set_album_context(self, artist, title, art_path=None):
        self._album_artist = artist
        self._album_title  = title
        self._track_title  = ''
        path = _note_path(artist, title)
        self._album_section.load(path, ctx1=artist, ctx2=title, art_path=art_path)
        self._track_section.clear()

    def set_track_context(self, artist, album_title, track_title):
        self._album_artist = artist
        self._album_title  = album_title
        self._track_title  = track_title
        path = _note_path(artist, album_title, track_title)
        self._track_section.load(path, ctx1=track_title)
        self._track_section.flush()

    def flush_all(self):
        self._album_section.flush()
        self._track_section.flush()

    def _on_mapped(self, _widget):
        self._album_section.reload()
        self._track_section.reload()

    @property
    def album_text_view(self):
        return self._album_section.text_view

    @property
    def track_text_view(self):
        return self._track_section.text_view


# ------------------------------------------------------------------ #
# helpers

def _note_path(artist, album_title, track_title=None):
    if track_title:
        fname = f'{_safe(artist)} - {_safe(album_title)} - {_safe(track_title)}.md'
    else:
        fname = f'{_safe(artist)} - {_safe(album_title)}.md'
    return NOTES_DIR / fname


def _safe(name: str) -> str:
    clean = ''.join(c if c.isalnum() or c in ' .-_' else '_' for c in (name or 'Unknown'))
    return clean.strip()[:60]
