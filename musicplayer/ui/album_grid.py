import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Adw, Pango, GObject, Gio

COVER_SIZE = 160


class AlbumItem(GObject.Object):
    __gtype_name__ = 'MusicPlayerAlbumItem'
    is_playing = GObject.Property(type=bool, default=False)

    def __init__(self, album_row):
        super().__init__()
        self.album_id     = album_row['id']
        self.album_title  = album_row['album_title']  or 'Unknown Album'
        self.album_artist = album_row['album_artist'] or 'Unknown Artist'
        self.art_path     = album_row['art_path']
        self.search_text  = f"{self.album_title} {self.album_artist}".lower()
        try:
            self.subtitle = album_row['subtitle'] or ''
        except (IndexError, KeyError):
            self.subtitle = ''


class _AlbumCardWidget(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class('album-card')
        self._current_item   = None
        self._notify_handler = None
        self._play_cb        = None

        cover_stack = Gtk.Stack()
        cover_stack.set_size_request(COVER_SIZE, COVER_SIZE)
        cover_stack.set_overflow(Gtk.Overflow.HIDDEN)
        cover_stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self._picture = Gtk.Picture()
        self._picture.set_content_fit(Gtk.ContentFit.COVER)
        self._picture.set_size_request(COVER_SIZE, COVER_SIZE)
        self._picture.set_hexpand(True)
        self._picture.set_vexpand(True)
        cover_stack.add_named(self._picture, 'art')

        self._drawing_area = Gtk.DrawingArea()
        self._drawing_area.set_size_request(COVER_SIZE, COVER_SIZE)
        self._drawing_area.set_draw_func(self._draw_placeholder, None)
        cover_stack.add_named(self._drawing_area, 'placeholder')

        cover_stack.set_visible_child_name('placeholder')
        self._cover_stack = cover_stack

        # Overlay wraps the cover so the play button floats over it
        cover_overlay = Gtk.Overlay()
        cover_overlay.set_size_request(COVER_SIZE, COVER_SIZE)
        cover_overlay.set_halign(Gtk.Align.CENTER)
        cover_overlay.set_child(cover_stack)

        self._play_btn = Gtk.Button()
        self._play_btn.set_icon_name('media-playback-start-symbolic')
        self._play_btn.add_css_class('album-play-btn')
        self._play_btn.set_halign(Gtk.Align.END)
        self._play_btn.set_valign(Gtk.Align.END)
        self._play_btn.set_margin_end(8)
        self._play_btn.set_margin_bottom(8)
        self._play_btn.set_visible(False)
        self._play_btn.connect('clicked', self._on_play_clicked)
        cover_overlay.add_overlay(self._play_btn)

        self.append(cover_overlay)

        motion = Gtk.EventControllerMotion()
        motion.connect('enter', lambda _c, _x, _y: self._play_btn.set_visible(True))
        motion.connect('leave', lambda _c: self._play_btn.set_visible(False))
        self.add_controller(motion)

        self._title_label = Gtk.Label()
        self._title_label.add_css_class('album-title')
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_label.set_max_width_chars(20)
        self._title_label.set_halign(Gtk.Align.START)
        self.append(self._title_label)

        self._artist_label = Gtk.Label()
        self._artist_label.add_css_class('album-artist')
        self._artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_label.set_max_width_chars(20)
        self._artist_label.set_halign(Gtk.Align.START)
        self.append(self._artist_label)

        self._subtitle_label = Gtk.Label()
        self._subtitle_label.add_css_class('album-subtitle')
        self._subtitle_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._subtitle_label.set_max_width_chars(20)
        self._subtitle_label.set_halign(Gtk.Align.START)
        self._subtitle_label.set_visible(False)
        self.append(self._subtitle_label)

    def _on_play_clicked(self, _btn):
        if self._play_cb and self._current_item:
            self._play_cb(self._current_item.album_id)

    def bind(self, item, play_cb=None):
        self._play_cb = play_cb
        self._current_item = item
        self._notify_handler = item.connect('notify::is-playing', self._on_playing_changed)
        self._title_label.set_text(item.album_title)
        self._artist_label.set_text(item.album_artist)
        self._subtitle_label.set_text(item.subtitle)
        self._subtitle_label.set_visible(bool(item.subtitle))
        self._update_playing_style(item.is_playing)

        if item.art_path:
            try:
                self._picture.set_filename(item.art_path)
                self._cover_stack.set_visible_child_name('art')
                return
            except Exception:
                pass

        self._cover_stack.set_visible_child_name('placeholder')
        self._drawing_area.queue_draw()

    def unbind(self):
        if self._notify_handler is not None and self._current_item is not None:
            self._current_item.disconnect(self._notify_handler)
        self._notify_handler = None
        self._current_item = None

    def _on_playing_changed(self, item, _pspec):
        self._update_playing_style(item.is_playing)

    def _update_playing_style(self, playing):
        if playing:
            self.add_css_class('album-card-playing')
        else:
            self.remove_css_class('album-card-playing')

    def _draw_placeholder(self, _area, cr, width, height, _data):
        item = self._current_item
        cr.set_source_rgb(0.040, 0.078, 0.133)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        if item:
            initials = _get_initials(item.album_artist, item.album_title)
            cr.set_source_rgb(0.216, 0.565, 0.867)
            cr.select_font_face('monospace', 0, 1)
            font_size = min(width, height) * 0.36
            cr.set_font_size(font_size)
            extents = cr.text_extents(initials)
            cr.move_to(
                (width  - extents.width)  / 2 - extents.x_bearing,
                (height - extents.height) / 2 - extents.y_bearing,
            )
            cr.show_text(initials)


def _get_initials(artist, album):
    parts = []
    for text in (artist, album):
        if text and text not in ('Unknown Artist', 'Unknown Album'):
            words = text.split()
            if words:
                parts.append(words[0][0].upper())
    return ''.join(parts[:2]) or '?'


class AlbumGridPage(Adw.NavigationPage):

    __gsignals__ = {
        'album-activated':      (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'album-play-requested': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'view-mode-changed':    (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self):
        super().__init__(title='Library')
        self.set_can_pop(False)
        self._search_query  = ''
        self._album_store   = Gio.ListStore(item_type=AlbumItem)
        self._view_btns     = {}
        self._view_mode     = 'library'
        self._updating_tabs = False
        self._build_ui()

    def _build_ui(self):
        # No per-page HeaderBar -- the window owns the header bar.
        self._inner_stack = Gtk.Stack()
        self._inner_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._inner_stack.set_hexpand(True)
        self._inner_stack.set_vexpand(True)
        self._inner_stack.add_named(self._build_scanning_view(), 'scanning')
        self._inner_stack.add_named(self._build_grid_view(),    'grid')
        self._inner_stack.set_visible_child_name('scanning')
        self.set_child(self._inner_stack)

    def _build_scanning_view(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_hexpand(True)
        box.set_vexpand(True)

        label = Gtk.Label(label='scanning library...')
        label.add_css_class('scanning-title')
        box.append(label)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_size_request(500, -1)
        box.append(self._progress_bar)

        self._progress_label = Gtk.Label(label='')
        self._progress_label.add_css_class('progress-label')
        self._progress_label.set_ellipsize(3)
        self._progress_label.set_max_width_chars(70)
        box.append(self._progress_label)

        return box

    def _build_grid_view(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.add_css_class('album-grid-outer')

        # --- View-mode tab bar ---
        tab_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tab_row.set_margin_start(14)
        tab_row.set_margin_end(14)
        tab_row.set_margin_top(10)
        tab_row.set_margin_bottom(8)

        tab_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tab_btns.add_css_class('linked')
        tab_btns.add_css_class('view-tab-group')

        for mode, label in (('library', 'Library'),
                             ('recent',  'Recent'),
                             ('top',     'Top Played')):
            btn = Gtk.ToggleButton(label=label)
            btn.add_css_class('view-tab-btn')
            btn.set_active(mode == 'library')
            btn.connect('toggled', self._on_view_tab_toggled, mode)
            tab_btns.append(btn)
            self._view_btns[mode] = btn

        tab_row.append(tab_btns)
        outer.append(tab_row)

        # --- Grid ---
        self._custom_filter = Gtk.CustomFilter.new(self._filter_func, None)
        self._filter_model  = Gtk.FilterListModel(
            model  = self._album_store,
            filter = self._custom_filter,
        )

        selection = Gtk.SingleSelection(model=self._filter_model)
        selection.set_autoselect(False)
        selection.set_can_unselect(True)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup',  self._on_factory_setup)
        factory.connect('bind',   self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)

        self._grid_view = Gtk.GridView(model=selection, factory=factory)
        self._grid_view.add_css_class('album-grid-view')
        self._grid_view.set_hexpand(True)
        self._grid_view.set_vexpand(True)
        self._grid_view.set_min_columns(2)
        self._grid_view.set_max_columns(12)
        self._grid_view.set_enable_rubberband(False)
        self._grid_view.set_single_click_activate(True)
        self._grid_view.connect('activate', self._on_activate)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._grid_view)
        outer.append(scrolled)
        return outer

    def _on_view_tab_toggled(self, btn, mode):
        if self._updating_tabs:
            return
        if not btn.get_active():
            self._updating_tabs = True
            btn.set_active(True)   # prevent deselecting the active tab
            self._updating_tabs = False
            return
        self._updating_tabs = True
        for m, b in self._view_btns.items():
            if m != mode:
                b.set_active(False)
        self._updating_tabs = False
        if mode != self._view_mode:
            self._view_mode = mode
            self.emit('view-mode-changed', mode)

    # ------------------------------------------------------------------ #
    # factory

    def _on_factory_setup(self, _f, li):
        li.set_child(_AlbumCardWidget())

    def _on_factory_bind(self, _f, li):
        li.get_child().bind(li.get_item(), play_cb=self._on_play_btn_clicked)

    def _on_play_btn_clicked(self, album_id):
        self.emit('album-play-requested', album_id)

    def _on_factory_unbind(self, _f, li):
        li.get_child().unbind()

    # ------------------------------------------------------------------ #
    # filter

    def _filter_func(self, item, _user_data):
        if not self._search_query:
            return True
        return self._search_query in item.search_text

    # ------------------------------------------------------------------ #
    # activation

    def _on_activate(self, _gv, position):
        item = self._filter_model.get_item(position)
        if item:
            self.emit('album-activated', item.album_id)

    # ------------------------------------------------------------------ #
    # public API

    def update_scan_progress(self, scanned, total, filename):
        if total > 0:
            self._progress_bar.set_fraction(scanned / total)
            self._progress_label.set_text(f'{scanned} / {total}  --  {filename}')
        else:
            self._progress_bar.pulse()
            self._progress_label.set_text('scanning...')

    def load_albums(self, albums):
        self._album_store.remove_all()
        for album_row in albums:
            self._album_store.append(AlbumItem(album_row))
        self._inner_stack.set_visible_child_name('grid')

    def apply_filter(self, query):
        self._search_query = query.lower()
        self._custom_filter.changed(Gtk.FilterChange.DIFFERENT)

    def set_playing_album(self, album_id):
        """Mark one album as playing; clear any previous playing marker."""
        for i in range(self._album_store.get_n_items()):
            item = self._album_store.get_item(i)
            item.is_playing = (item.album_id == album_id)
