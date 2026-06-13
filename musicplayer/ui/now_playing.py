import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango


class NowPlayingBar(Gtk.Box):
    """Bottom bar: shuffle / prev / play-pause / next / repeat | title+artist | scrubber | time | volume"""

    def __init__(self, player,
                 on_prev=None, on_next=None, on_album_jump=None,
                 on_shuffle_changed=None, on_repeat_changed=None,
                 on_volume_changed=None, initial_volume=1.0):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.add_css_class('now-playing-bar')
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(6)
        self.set_margin_bottom(6)

        self._player             = player
        self._on_prev            = on_prev
        self._on_next            = on_next
        self._on_album_jump      = on_album_jump
        self._shuffle_cb         = on_shuffle_changed
        self._repeat_cb          = on_repeat_changed
        self._volume_cb          = on_volume_changed
        self._repeat_mode        = 'none'

        # --- Shuffle ---
        self._shuffle_btn = Gtk.ToggleButton()
        self._shuffle_btn.set_icon_name('media-playlist-shuffle-symbolic')
        self._shuffle_btn.add_css_class('flat')
        self._shuffle_btn.add_css_class('circular')
        self._shuffle_btn.add_css_class('mode-btn')
        self._shuffle_btn.set_valign(Gtk.Align.CENTER)
        self._shuffle_btn.set_tooltip_text('shuffle')
        self._shuffle_btn.connect('toggled', self._on_shuffle_toggled)
        self.append(self._shuffle_btn)

        # --- Transport ---
        prev_btn = Gtk.Button()
        prev_btn.set_icon_name('media-skip-backward-symbolic')
        prev_btn.add_css_class('flat')
        prev_btn.add_css_class('circular')
        prev_btn.set_valign(Gtk.Align.CENTER)
        prev_btn.set_tooltip_text('previous track')
        prev_btn.connect('clicked', lambda _b: self._on_prev and self._on_prev())
        self.append(prev_btn)

        self._pp_btn = Gtk.Button()
        self._pp_btn.set_icon_name('media-playback-start-symbolic')
        self._pp_btn.add_css_class('flat')
        self._pp_btn.add_css_class('circular')
        self._pp_btn.set_valign(Gtk.Align.CENTER)
        self._pp_btn.set_tooltip_text('play / pause')
        self._pp_btn.connect('clicked', lambda _b: self._player.toggle())
        self.append(self._pp_btn)

        next_btn = Gtk.Button()
        next_btn.set_icon_name('media-skip-forward-symbolic')
        next_btn.add_css_class('flat')
        next_btn.add_css_class('circular')
        next_btn.set_valign(Gtk.Align.CENTER)
        next_btn.set_tooltip_text('next track')
        next_btn.connect('clicked', lambda _b: self._on_next and self._on_next())
        self.append(next_btn)

        # --- Repeat (cycles none -> album -> track -> none) ---
        self._repeat_btn = Gtk.Button()
        self._repeat_btn.add_css_class('flat')
        self._repeat_btn.add_css_class('circular')
        self._repeat_btn.add_css_class('mode-btn')
        self._repeat_btn.set_valign(Gtk.Align.CENTER)
        self._repeat_btn.set_tooltip_text('repeat: off')
        self._repeat_btn.connect('clicked', self._on_repeat_clicked)

        repeat_box = Gtk.Box(spacing=1)
        repeat_box.set_halign(Gtk.Align.CENTER)
        repeat_box.set_valign(Gtk.Align.CENTER)
        self._repeat_icon = Gtk.Image.new_from_icon_name('media-playlist-repeat-symbolic')
        self._repeat_one_lbl = Gtk.Label(label='1')
        self._repeat_one_lbl.add_css_class('repeat-one-badge')
        self._repeat_one_lbl.set_visible(False)
        repeat_box.append(self._repeat_icon)
        repeat_box.append(self._repeat_one_lbl)
        self._repeat_btn.set_child(repeat_box)
        self.append(self._repeat_btn)

        # --- Track info (clickable, jumps to album) ---
        track_labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        track_labels.set_valign(Gtk.Align.CENTER)

        self._title_lbl = Gtk.Label(label='nothing playing')
        self._title_lbl.add_css_class('now-playing-title')
        self._title_lbl.set_halign(Gtk.Align.START)
        self._title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_lbl.set_max_width_chars(30)
        track_labels.append(self._title_lbl)

        self._artist_lbl = Gtk.Label(label='')
        self._artist_lbl.add_css_class('now-playing-artist')
        self._artist_lbl.set_halign(Gtk.Align.START)
        self._artist_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_lbl.set_max_width_chars(30)
        track_labels.append(self._artist_lbl)

        jump_btn = Gtk.Button()
        jump_btn.add_css_class('flat')
        jump_btn.add_css_class('now-playing-jump-btn')
        jump_btn.set_tooltip_text('open album track list')
        jump_btn.set_child(track_labels)
        jump_btn.set_valign(Gtk.Align.CENTER)
        jump_btn.connect('clicked', lambda _b: self._on_album_jump and self._on_album_jump())
        self.append(jump_btn)

        # --- Scrubber (takes remaining space) ---
        scrubber_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrubber_box.set_hexpand(True)
        scrubber_box.set_valign(Gtk.Align.CENTER)

        self._scrubber = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self._scrubber.set_range(0.0, 1.0)
        self._scrubber.set_value(0.0)
        self._scrubber.set_draw_value(False)
        self._scrubber.set_hexpand(True)
        self._scrubber.add_css_class('now-playing-scrubber')
        self._scrubber.connect('change-value', self._on_seek)
        scrubber_box.append(self._scrubber)
        self.append(scrubber_box)

        # --- Time ---
        self._time_lbl = Gtk.Label(label='0:00')
        self._time_lbl.add_css_class('now-playing-time')
        self._time_lbl.set_valign(Gtk.Align.CENTER)
        self._time_lbl.set_width_chars(5)
        self.append(self._time_lbl)

        # --- Volume ---
        vol_icon = Gtk.Image.new_from_icon_name('audio-volume-medium-symbolic')
        vol_icon.set_valign(Gtk.Align.CENTER)
        self.append(vol_icon)

        self._vol_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self._vol_scale.set_range(0.0, 1.0)
        self._vol_scale.set_value(initial_volume)
        self._vol_scale.set_draw_value(False)
        self._vol_scale.set_size_request(80, -1)
        self._vol_scale.set_valign(Gtk.Align.CENTER)
        self._vol_scale.add_css_class('volume-scale')
        self._vol_scale.connect('value-changed', self._on_vol_changed)
        self.append(self._vol_scale)

    # ------------------------------------------------------------------ #
    # internal handlers

    def _on_shuffle_toggled(self, btn):
        if self._shuffle_cb:
            self._shuffle_cb(btn.get_active())

    def _on_repeat_clicked(self, _btn):
        modes = ['none', 'album', 'track']
        self._repeat_mode = modes[(modes.index(self._repeat_mode) + 1) % 3]
        self._sync_repeat_visual()
        if self._repeat_cb:
            self._repeat_cb(self._repeat_mode)

    def _sync_repeat_visual(self):
        if self._repeat_mode == 'none':
            self._repeat_btn.set_tooltip_text('repeat: off')
            self._repeat_btn.remove_css_class('active-mode')
            self._repeat_one_lbl.set_visible(False)
        elif self._repeat_mode == 'album':
            self._repeat_btn.set_tooltip_text('repeat: album')
            self._repeat_btn.add_css_class('active-mode')
            self._repeat_one_lbl.set_visible(False)
        else:
            self._repeat_btn.set_tooltip_text('repeat: track')
            self._repeat_btn.add_css_class('active-mode')
            self._repeat_one_lbl.set_visible(True)

    def _on_vol_changed(self, scale):
        if self._volume_cb:
            self._volume_cb(scale.get_value())

    def _on_seek(self, _scale, _scroll_type, value):
        self._player.seek(max(0.0, min(1.0, value)))
        return False

    # ------------------------------------------------------------------ #
    # public API

    def update_track(self, title, artist):
        self._title_lbl.set_text(title or 'Unknown Track')
        self._artist_lbl.set_text(artist or '')
        self._scrubber.set_value(0.0)
        self._time_lbl.set_text('0:00')

    def update_position(self, fraction, pos_sec, _dur_sec):
        self._scrubber.set_value(fraction)
        m, s = divmod(int(pos_sec), 60)
        self._time_lbl.set_text(f'{m}:{s:02d}')

    def update_state(self, state):
        from musicplayer.player import PlayState
        icon = ('media-playback-pause-symbolic'
                if state == PlayState.PLAYING
                else 'media-playback-start-symbolic')
        self._pp_btn.set_icon_name(icon)
