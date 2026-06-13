import gi
import random
import time as _time
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Adw, GLib, Pango

from musicplayer import config as config_module
from musicplayer import database
from musicplayer.mpris import MPRISService
from musicplayer.player import Player, PlayState
from musicplayer.scanner import Scanner
from musicplayer.themes import get_theme
from musicplayer.ui.mascot import MascotWidget, GazeTarget
from musicplayer.ui.notes import NotesPane
from musicplayer.ui.now_playing import NowPlayingBar
from musicplayer.ui.onboarding import OnboardingPage
from musicplayer.ui.album_grid import AlbumGridPage
from musicplayer.ui.track_list import TrackListPage
from musicplayer.ui.prefs import PrefsDialog


class MainWindow(Adw.ApplicationWindow):

    def __init__(self, initial_theme: str = 'technics-blue', **kwargs):
        super().__init__(**kwargs)
        self.set_title('musicplayer')
        self.set_default_size(1280, 820)

        self._current_theme     = initial_theme
        self._config            = config_module.load_config()
        self._scanner           = None
        self._current_album     = None
        self._current_album_id  = None
        self._current_art_path  = None
        self._current_tracks    = []
        self._current_track_idx = -1
        self._track_page        = None
        self._left_panel_artist = ''
        self._left_panel_title  = ''

        self._shuffle        = False
        self._shuffle_order  = []
        self._shuffle_pos    = -1
        self._repeat_mode    = 'none'
        self._view_mode      = 'library'
        self._vol_save_timer = None

        self._build_ui()
        self._decide_first_view()

        self._mpris = MPRISService(
            on_play_pause = self._player.toggle,
            on_next       = self._play_next,
            on_previous   = self._play_prev,
            on_stop       = self._player.stop,
        )

        self.connect('notify::focus-widget', self._on_focus_changed)

    # ------------------------------------------------------------------ #
    # layout

    def _build_ui(self):
        self._player = Player(
            on_state_changed = self._on_player_state,
            on_position      = self._on_player_position,
            on_error         = self._on_player_error,
            on_track_ended   = self._on_track_ended,
            on_level         = self._on_audio_level,
        )

        outer = Adw.ToolbarView()

        # --- Thin header bar ---
        self._header = Adw.HeaderBar()
        self._header.add_css_class('flat')
        self._header.add_css_class('main-header')
        self._header.set_show_back_button(False)

        self._back_btn = Gtk.Button()
        self._back_btn.set_icon_name('go-previous-symbolic')
        self._back_btn.add_css_class('flat')
        self._back_btn.set_tooltip_text('back to library')
        self._back_btn.set_visible(False)
        self._back_btn.connect('clicked', self._on_back_clicked)
        self._header.pack_start(self._back_btn)

        self._notes_btn = Gtk.ToggleButton()
        self._notes_btn.set_icon_name('document-edit-symbolic')
        self._notes_btn.add_css_class('flat')
        self._notes_btn.set_tooltip_text('show / hide notes')
        self._notes_btn.set_visible(False)
        self._notes_btn.connect('toggled', self._on_notes_btn_toggled)
        self._header.pack_end(self._notes_btn)

        self._prefs_btn = Gtk.Button()
        self._prefs_btn.set_icon_name('preferences-system-symbolic')
        self._prefs_btn.add_css_class('flat')
        self._prefs_btn.set_tooltip_text('appearance settings')
        self._prefs_btn.connect('clicked', self._on_prefs_clicked)
        self._header.pack_end(self._prefs_btn)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text('search albums, artists, tracks...')
        self._search_entry.set_hexpand(True)
        self._search_entry.connect('search-changed', self._on_search_changed)

        self._header_title = Gtk.Label()
        self._header_title.add_css_class('header-album-title')

        self._title_stack = Gtk.Stack()
        self._title_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._title_stack.set_transition_duration(80)
        self._title_stack.add_named(self._search_entry, 'search')
        self._title_stack.add_named(self._header_title, 'title')
        self._title_stack.set_visible_child_name('search')
        self._header.set_title_widget(self._title_stack)

        outer.add_top_bar(self._header)

        # --- Left panel: mascot (fixed size) + spacer + album info ------
        self._left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._left_panel.set_size_request(260, -1)
        self._left_panel.set_hexpand(False)
        self._left_panel.add_css_class('left-panel')

        self._mascot = MascotWidget()
        self._mascot.set_size_request(220, 180)
        self._mascot.set_halign(Gtk.Align.CENTER)
        self._mascot.set_valign(Gtk.Align.START)
        self._mascot.set_margin_top(20)
        self._left_panel.append(self._mascot)
        self._apply_mascot_theme(self._current_theme)

        _spacer = Gtk.Box()
        _spacer.set_vexpand(True)
        self._left_panel.append(_spacer)

        self._left_album_box = self._build_left_album_box()
        self._left_panel.append(self._left_album_box)

        # --- Center: Stack for in-place content swap (no push/pop) ------
        self._center_stack = Gtk.Stack()
        self._center_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._center_stack.set_transition_duration(80)
        self._center_stack.set_hexpand(True)
        self._center_stack.set_vexpand(True)

        self._album_page = AlbumGridPage()
        self._album_page.connect('album-activated',      self._on_album_activated)
        self._album_page.connect('album-play-requested', self._on_album_play_requested)
        self._album_page.connect('view-mode-changed',    self._on_view_mode_changed)
        self._center_stack.add_named(self._album_page, 'grid')

        self._onboarding_page = OnboardingPage()
        self._onboarding_page.connect('folder-chosen', self._on_folder_chosen)
        self._center_stack.add_named(self._onboarding_page, 'onboarding')

        # Notes sidebar wraps the center stack
        self._notes_pane = NotesPane()

        self._split_view = Adw.OverlaySplitView()
        self._split_view.set_sidebar_position(Gtk.PackType.END)
        self._split_view.set_collapsed(False)
        self._split_view.set_show_sidebar(False)
        self._split_view.set_min_sidebar_width(280)
        self._split_view.set_max_sidebar_width(420)
        self._split_view.set_content(self._center_stack)
        self._split_view.set_sidebar(self._notes_pane)
        self._split_view.set_hexpand(True)

        # Paned hard-pins the left panel width regardless of child natural sizes
        content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        content_paned.add_css_class('main-split')
        content_paned.set_position(260)
        content_paned.set_resize_start_child(False)
        content_paned.set_shrink_start_child(False)
        content_paned.set_resize_end_child(True)
        content_paned.set_shrink_end_child(False)
        content_paned.set_start_child(self._left_panel)
        content_paned.set_end_child(self._split_view)
        outer.set_content(content_paned)

        # --- Now-playing bar --------------------------------------------
        self._now_playing = NowPlayingBar(
            self._player,
            on_prev            = self._play_prev,
            on_next            = self._play_next,
            on_album_jump      = self._on_jump_to_album,
            on_shuffle_changed = self._on_shuffle_changed,
            on_repeat_changed  = self._on_repeat_changed,
            on_volume_changed  = self._on_volume_changed,
            initial_volume     = self._config.get('volume', 1.0),
        )
        self._player.set_volume(self._config.get('volume', 1.0))
        outer.add_bottom_bar(self._now_playing)

        self.set_content(outer)

    def _build_left_album_box(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.add_css_class('left-album-info')
        box.set_visible(False)

        # Text labels above the art
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_margin_start(12)
        text_box.set_margin_end(12)
        text_box.set_margin_top(10)
        text_box.set_margin_bottom(6)

        self._left_title_lbl = Gtk.Label()
        self._left_title_lbl.add_css_class('left-album-title')
        self._left_title_lbl.set_xalign(0)
        self._left_title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._left_title_lbl.set_max_width_chars(18)
        text_box.append(self._left_title_lbl)

        self._left_artist_lbl = Gtk.Label()
        self._left_artist_lbl.add_css_class('left-album-artist')
        self._left_artist_lbl.set_xalign(0)
        self._left_artist_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._left_artist_lbl.set_max_width_chars(18)
        text_box.append(self._left_artist_lbl)

        box.append(text_box)

        # Album art below text -- narrower than the panel, fixed height
        self._left_art_stack = Gtk.Stack()
        self._left_art_stack.set_size_request(200, 130)
        self._left_art_stack.set_halign(Gtk.Align.CENTER)
        self._left_art_stack.set_margin_bottom(12)
        self._left_art_stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self._left_art_picture = Gtk.Picture()
        self._left_art_picture.set_content_fit(Gtk.ContentFit.COVER)
        self._left_art_picture.set_size_request(200, 130)
        self._left_art_stack.add_named(self._left_art_picture, 'art')

        self._left_art_placeholder = Gtk.DrawingArea()
        self._left_art_placeholder.set_size_request(200, 130)
        self._left_art_placeholder.set_draw_func(self._draw_left_placeholder, None)
        self._left_art_stack.add_named(self._left_art_placeholder, 'placeholder')
        self._left_art_stack.set_visible_child_name('placeholder')

        box.append(self._left_art_stack)
        return box

    def _draw_left_placeholder(self, _area, cr, w, h, _data):
        t = get_theme(self._current_theme)
        r, g, b = self._hex_to_rgb(t['art_bg'])
        cr.set_source_rgb(r, g, b)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        initials = self._get_initials(self._left_panel_artist, self._left_panel_title)
        ar, ag, ab = self._hex_to_rgb(t['accent'])
        cr.set_source_rgb(ar, ag, ab)
        cr.select_font_face('monospace', 0, 1)
        font_size = min(w, h) * 0.36
        cr.set_font_size(font_size)
        extents = cr.text_extents(initials)
        cr.move_to(
            (w - extents.width)  / 2 - extents.x_bearing,
            (h - extents.height) / 2 - extents.y_bearing,
        )
        cr.show_text(initials)

    @staticmethod
    def _hex_to_rgb(hex_color: str):
        h = hex_color.lstrip('#')
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    @staticmethod
    def _get_initials(artist, album):
        parts = []
        for text in (artist, album):
            if text and text not in ('Unknown Artist', 'Unknown Album'):
                words = text.split()
                if words:
                    parts.append(words[0][0].upper())
        return ''.join(parts[:2]) or '?'

    def _show_left_album(self, artist, title, art_path=None):
        self._left_panel_artist = artist
        self._left_panel_title  = title
        self._left_title_lbl.set_text(title)
        self._left_artist_lbl.set_text(artist)
        if art_path:
            try:
                self._left_art_picture.set_filename(art_path)
                self._left_art_stack.set_visible_child_name('art')
            except Exception:
                self._left_art_stack.set_visible_child_name('placeholder')
                self._left_art_placeholder.queue_draw()
        else:
            self._left_art_stack.set_visible_child_name('placeholder')
            self._left_art_placeholder.queue_draw()
        self._left_album_box.set_visible(True)

    def _hide_left_album(self):
        self._left_album_box.set_visible(False)
        self._left_panel_artist = ''
        self._left_panel_title  = ''

    def _decide_first_view(self):
        if config_module.has_music_folders(self._config):
            self._center_stack.set_visible_child_name('grid')
            self._notes_btn.set_visible(True)
            self._start_scan()
        else:
            self._center_stack.set_visible_child_name('onboarding')

    # ------------------------------------------------------------------ #
    # header state helpers

    def _enter_grid_mode(self):
        self._back_btn.set_visible(False)
        self._notes_btn.set_visible(True)
        self._title_stack.set_visible_child_name('search')
        self._search_entry.set_text('')
        self._album_page.apply_filter('')

    def _enter_track_mode(self, title: str):
        self._back_btn.set_visible(True)
        self._notes_btn.set_visible(True)
        self._title_stack.set_visible_child_name('title')
        self._header_title.set_text(title)

    def _on_back_clicked(self, _btn):
        self._center_stack.set_visible_child_name('grid')
        self._enter_grid_mode()

    def _on_search_changed(self, entry):
        self._album_page.apply_filter(entry.get_text().strip())

    # ------------------------------------------------------------------ #
    # onboarding

    def _on_folder_chosen(self, _page, folder_path):
        self._config['music_folders'] = [folder_path]
        config_module.save_config(self._config)
        self._center_stack.set_visible_child_name('grid')
        self._notes_btn.set_visible(True)
        self._start_scan()

    # ------------------------------------------------------------------ #
    # scanner

    def _start_scan(self):
        self._mascot.set_spinning(True)
        self._scanner = Scanner(
            music_folders = self._config.get('music_folders', []),
            on_progress   = self._on_scan_progress,
            on_complete   = self._on_scan_complete,
            on_error      = self._on_scan_error,
        )
        self._scanner.start()

    def _on_scan_progress(self, scanned, total, filename):
        self._album_page.update_scan_progress(scanned, total, filename)
        return GLib.SOURCE_REMOVE

    def _on_scan_complete(self, album_count, track_count):
        conn   = database.get_connection()
        albums = database.get_all_albums(conn)
        conn.close()
        self._album_page.load_albums(albums)
        self._mascot.set_spinning(False)
        return GLib.SOURCE_REMOVE

    def _on_scan_error(self, error_message):
        self._mascot.set_spinning(False)
        dialog = Adw.MessageDialog(
            transient_for = self,
            heading       = 'scan error',
            body          = error_message,
        )
        dialog.add_response('ok', 'ok')
        dialog.present()
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ #
    # album -> track list (in-place stack swap, no push)

    def _on_album_activated(self, _page, album_id):
        conn       = database.get_connection()
        tracks     = database.get_tracks_for_album(conn, album_id)
        album_rows = conn.execute(
            'SELECT album_title, album_artist, art_path FROM albums WHERE id = ?',
            (album_id,)
        ).fetchone()
        conn.close()

        if not album_rows:
            return

        artist   = album_rows['album_artist'] or 'Unknown Artist'
        title    = album_rows['album_title']  or 'Unknown Album'
        art_path = album_rows['art_path']

        self._current_album     = (artist, title)
        self._current_album_id  = album_id
        self._current_art_path  = art_path
        self._current_tracks    = [dict(t) for t in tracks]
        self._current_track_idx = -1
        self._shuffle_order     = []
        self._shuffle_pos       = -1
        if self._shuffle:
            self._build_shuffle_order()

        # Swap out old track page before adding new one
        old = self._center_stack.get_child_by_name('tracks')
        if old:
            self._center_stack.remove(old)

        self._track_page = TrackListPage(
            album_title  = title,
            album_artist = artist,
            tracks       = tracks,
        )
        self._track_page.connect('track-activated', self._on_track_activated)
        self._center_stack.add_named(self._track_page, 'tracks')
        self._center_stack.set_visible_child_name('tracks')

        self._enter_track_mode(title)
        self._notes_pane.set_album_context(artist, title, art_path=art_path)
        self._show_left_album(artist, title, art_path)

    def _on_album_play_requested(self, _page, album_id):
        """Play button on album card -- start playing without navigating to track list."""
        conn       = database.get_connection()
        tracks     = database.get_tracks_for_album(conn, album_id)
        album_rows = conn.execute(
            'SELECT album_title, album_artist, art_path FROM albums WHERE id = ?',
            (album_id,)
        ).fetchone()
        conn.close()

        if not album_rows or not tracks:
            return

        artist   = album_rows['album_artist'] or 'Unknown Artist'
        title    = album_rows['album_title']  or 'Unknown Album'
        art_path = album_rows['art_path']

        self._current_album     = (artist, title)
        self._current_album_id  = album_id
        self._current_art_path  = art_path
        self._current_tracks    = [dict(t) for t in tracks]
        self._current_track_idx = -1
        self._shuffle_order     = []
        self._shuffle_pos       = -1
        if self._shuffle:
            self._build_shuffle_order()

        self._show_left_album(artist, title, art_path)
        self._play_track_at(0)

    # ------------------------------------------------------------------ #
    # playback

    def _on_track_activated(self, _page, file_path, title, artist):
        for i, t in enumerate(self._current_tracks):
            if t['file_path'] == file_path:
                self._current_track_idx = i
                break

        self._player.play(file_path)
        conn = database.get_connection()
        database.record_play(conn, file_path)
        conn.close()
        self._now_playing.update_track(title, artist)

        if self._current_album_id:
            self._album_page.set_playing_album(self._current_album_id)

        if self._current_album:
            self._notes_pane.set_track_context(
                self._current_album[0], self._current_album[1], title
            )

        if self._track_page:
            self._track_page.highlight_track(file_path)

        album = self._current_album[1] if self._current_album else ''
        self._mpris.set_track(
            title, artist, album, self._current_art_path,
            self._current_track_idx, len(self._current_tracks),
        )

    def _play_prev(self):
        if not self._current_tracks:
            return
        if self._shuffle and self._shuffle_order:
            prev_pos = max(0, self._shuffle_pos - 1)
            self._shuffle_pos = prev_pos
            self._play_track_at(self._shuffle_order[prev_pos])
        else:
            self._play_track_at(max(0, self._current_track_idx - 1))

    def _play_next(self):
        if not self._current_tracks:
            return
        if self._shuffle and self._shuffle_order:
            next_pos = self._shuffle_pos + 1
            if next_pos >= len(self._shuffle_order):
                if self._repeat_mode in ('album', 'track'):
                    self._build_shuffle_order()
                    next_pos = 0
                else:
                    return
            self._shuffle_pos = next_pos
            self._play_track_at(self._shuffle_order[next_pos])
        else:
            idx = self._current_track_idx + 1
            if idx >= len(self._current_tracks):
                if self._repeat_mode in ('album', 'track'):
                    idx = 0
                else:
                    return
            self._play_track_at(idx)

    def _build_shuffle_order(self):
        indices = list(range(len(self._current_tracks)))
        if self._current_track_idx in indices:
            indices.remove(self._current_track_idx)
        random.shuffle(indices)
        self._shuffle_order = indices
        self._shuffle_pos   = -1

    def _play_track_at(self, idx):
        if not (0 <= idx < len(self._current_tracks)):
            return
        t                       = self._current_tracks[idx]
        self._current_track_idx = idx
        title  = t.get('title')  or 'Unknown Track'
        artist = t.get('artist') or t.get('album_artist') or 'Unknown Artist'
        self._player.play(t['file_path'])
        conn = database.get_connection()
        database.record_play(conn, t['file_path'])
        conn.close()
        self._now_playing.update_track(title, artist)
        if self._current_album:
            self._notes_pane.set_track_context(
                self._current_album[0], self._current_album[1], title
            )
        if self._track_page:
            self._track_page.highlight_track(t['file_path'])
        album = self._current_album[1] if self._current_album else ''
        self._mpris.set_track(
            title, artist, album, self._current_art_path,
            idx, len(self._current_tracks),
        )

    def _on_player_state(self, state):
        self._now_playing.update_state(state)
        self._mascot.set_spinning(state == PlayState.PLAYING)
        if state != PlayState.PLAYING:
            self._mascot.reset_vu()
        status = {
            PlayState.PLAYING: 'Playing',
            PlayState.PAUSED:  'Paused',
            PlayState.STOPPED: 'Stopped',
        }.get(state, 'Stopped')
        self._mpris.set_playback_status(status)

    def _on_audio_level(self, left_db, right_db):
        self._mascot.set_vu_levels(left_db, right_db)

    def _on_player_position(self, fraction, pos_sec, dur_sec):
        self._now_playing.update_position(fraction, pos_sec, dur_sec)

    def _on_player_error(self, message):
        dialog = Adw.MessageDialog(
            transient_for = self,
            heading       = 'playback error',
            body          = message,
        )
        dialog.add_response('ok', 'ok')
        dialog.present()

    def _on_track_ended(self):
        if self._repeat_mode == 'track':
            self._play_track_at(self._current_track_idx)
        else:
            self._play_next()

    def _on_jump_to_album(self):
        if not self._current_album_id:
            return
        if self._center_stack.get_visible_child_name() == 'tracks':
            return
        self._on_album_activated(None, self._current_album_id)

    # ------------------------------------------------------------------ #
    # shuffle / repeat / volume / view mode

    def _on_shuffle_changed(self, active: bool):
        self._shuffle = active
        if active and self._current_tracks:
            self._build_shuffle_order()
        else:
            self._shuffle_order = []
            self._shuffle_pos   = -1
        self._mpris.set_shuffle(active)

    def _on_repeat_changed(self, mode: str):
        self._repeat_mode = mode
        loop = {'none': 'None', 'album': 'Playlist', 'track': 'Track'}.get(mode, 'None')
        self._mpris.set_loop_status(loop)

    def _on_volume_changed(self, v: float):
        self._player.set_volume(v)
        if self._vol_save_timer:
            GLib.source_remove(self._vol_save_timer)
        self._vol_save_timer = GLib.timeout_add(800, self._save_volume_config)

    def _save_volume_config(self):
        self._config['volume'] = self._player.volume
        config_module.save_config(self._config)
        self._vol_save_timer = None
        return GLib.SOURCE_REMOVE

    def _on_view_mode_changed(self, _page, mode: str):
        self._view_mode = mode
        conn = database.get_connection()
        if mode == 'recent':
            rows   = database.get_recently_played_albums(conn, limit=50)
            albums = [dict(r) | {'subtitle': self._format_age(r['last_played'])}
                      for r in rows]
        elif mode == 'top':
            rows   = database.get_most_played_albums(conn, limit=50)
            albums = [dict(r) | {'subtitle': f"{r['play_count']} play{'s' if r['play_count'] != 1 else ''}"}
                      for r in rows]
        else:
            albums = database.get_all_albums(conn)
        conn.close()
        self._album_page.load_albums(albums)

    @staticmethod
    def _format_age(ts: int) -> str:
        age = _time.time() - ts
        if age < 60:
            return 'just now'
        if age < 3600:
            m = int(age / 60)
            return f'{m}m ago'
        if age < 86400:
            return f'{int(age / 3600)}h ago'
        if age < 7 * 86400:
            return f'{int(age / 86400)}d ago'
        if age < 365 * 86400:
            return f'{int(age / (7 * 86400))}w ago'
        return f'{int(age / (365 * 86400))}y ago'

    # ------------------------------------------------------------------ #
    # preferences

    def _on_prefs_clicked(self, _btn):
        dlg = PrefsDialog(current_theme_key=self._current_theme)
        dlg.connect('theme-selected', self._on_theme_selected)
        dlg.present(self)

    def _on_theme_selected(self, _dlg, theme_key: str):
        self._current_theme = theme_key
        self._apply_mascot_theme(theme_key)
        self._left_art_placeholder.queue_draw()
        app = self.get_application()
        if app:
            app.apply_theme(theme_key)
        self._config['theme'] = theme_key
        config_module.save_config(self._config)

    def _apply_mascot_theme(self, theme_key: str):
        t = get_theme(theme_key)
        self._mascot.set_theme_colors(
            bg     = t['mascot_bg'],
            border = t['mascot_border'],
            accent = t['mascot_accent'],
            eye    = t.get('mascot_eye'),
        )

    # ------------------------------------------------------------------ #
    # notes pane

    def _on_notes_btn_toggled(self, btn):
        self._split_view.set_show_sidebar(btn.get_active())

    # ------------------------------------------------------------------ #
    # mascot gaze

    def _on_focus_changed(self, win, _pspec):
        focused = win.get_focus()
        if focused is None:
            self._mascot.set_gaze(GazeTarget.DOWN_RIGHT)
            return

        notes_tvs = {self._notes_pane.album_text_view,
                     self._notes_pane.track_text_view}
        w = focused
        while w is not None:
            if isinstance(w, Gtk.SearchEntry):
                self._mascot.set_gaze(GazeTarget.RIGHT)
                return
            if w in notes_tvs or isinstance(w, Gtk.TextView):
                self._mascot.set_gaze(GazeTarget.FAR_RIGHT)
                return
            w = w.get_parent()

        self._mascot.set_gaze(GazeTarget.DOWN_RIGHT)
