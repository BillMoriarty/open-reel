import math
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

from musicplayer.database import DATA_DIR
from musicplayer.themes import THEMES

NOTES_DIR = DATA_DIR / 'notes'


class _ThemeSwatch(Gtk.DrawingArea):
    """Mini colour swatch showing the theme palette."""

    def __init__(self, theme: dict):
        super().__init__()
        self._t = theme
        self.set_size_request(52, 34)
        self.set_draw_func(self._draw, None)

    def _draw(self, _area, cr, w, h, _data):
        t = self._t
        r = 5

        def rrect(x, y, bw, bh, rad):
            cr.new_path()
            cr.arc(x+rad,    y+rad,    rad, math.pi,     3*math.pi/2)
            cr.arc(x+bw-rad, y+rad,    rad, 3*math.pi/2, 0)
            cr.arc(x+bw-rad, y+bh-rad, rad, 0,           math.pi/2)
            cr.arc(x+rad,    y+bh-rad, rad, math.pi/2,   math.pi)
            cr.close_path()

        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))

        # Background
        rrect(0, 0, w, h, r)
        cr.set_source_rgb(*hex_to_rgb(t['window_bg']))
        cr.fill()

        # Header strip
        cr.rectangle(0, 0, w, 10)
        cr.set_source_rgb(*hex_to_rgb(t['header_bg']))
        cr.fill()

        # Accent bar
        cr.rectangle(4, 13, 18, 4)
        cr.set_source_rgb(*hex_to_rgb(t['accent']))
        cr.fill()

        # Dim bar (simulates text)
        cr.rectangle(4, 20, 12, 3)
        cr.set_source_rgb(*hex_to_rgb(t['fg_dim']))
        cr.fill()

        # Card swatch
        rrect(w-22, 11, 18, 16, 3)
        cr.set_source_rgb(*hex_to_rgb(t['card_bg']))
        cr.fill_preserve()
        cr.set_source_rgb(*hex_to_rgb(t['card_border']))
        cr.set_line_width(0.8)
        cr.stroke()

        # Border outline
        rrect(0, 0, w, h, r)
        cr.set_source_rgba(*hex_to_rgb(t['border']), 0.8)
        cr.set_line_width(1)
        cr.stroke()


class PrefsDialog(Adw.Dialog):

    __gsignals__ = {
        'theme-selected':    (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'folders-changed':   (GObject.SignalFlags.RUN_LAST, None, ()),
        'rescan-requested':  (GObject.SignalFlags.RUN_LAST, None, ()),
        'font-selected':     (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, current_theme_key: str, music_folders: list, current_font: str = ''):
        super().__init__()
        self.set_title('Settings')
        self.set_content_width(380)
        self.set_content_height(520)
        self._current       = current_theme_key
        self._current_font  = current_font
        self._folders       = list(music_folders)
        self._rows          = {}
        self._folder_rows   = {}
        self._build_ui()

    def get_folders(self):
        return list(self._folders)

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Adw.HeaderBar()
        header.add_css_class('flat')
        outer.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_margin_top(16)
        body.set_margin_bottom(20)
        body.set_margin_start(20)
        body.set_margin_end(20)

        # ---- Music Folders section ----
        folders_lbl = Gtk.Label(label='MUSIC FOLDERS')
        folders_lbl.add_css_class('notes-section-title')
        folders_lbl.set_halign(Gtk.Align.START)
        body.append(folders_lbl)

        self._folders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.append(self._folders_box)
        self._rebuild_folder_rows()

        folder_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        add_btn = Gtk.Button(label='+ add folder')
        add_btn.add_css_class('flat')
        add_btn.connect('clicked', self._on_add_folder)
        folder_btns.append(add_btn)

        self._rescan_btn = Gtk.Button(label='rescan library')
        self._rescan_btn.add_css_class('flat')
        self._rescan_btn.connect('clicked', self._on_rescan_clicked)
        folder_btns.append(self._rescan_btn)

        body.append(folder_btns)

        body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ---- Notes section ----
        notes_lbl = Gtk.Label(label='NOTES')
        notes_lbl.add_css_class('notes-section-title')
        notes_lbl.set_halign(Gtk.Align.START)
        body.append(notes_lbl)

        notes_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        notes_row.set_valign(Gtk.Align.CENTER)

        notes_path_lbl = Gtk.Label(label=str(NOTES_DIR))
        notes_path_lbl.add_css_class('notes-context')
        notes_path_lbl.set_halign(Gtk.Align.START)
        notes_path_lbl.set_hexpand(True)
        notes_path_lbl.set_ellipsize(3)
        notes_row.append(notes_path_lbl)

        open_notes_btn = Gtk.Button(label='open folder')
        open_notes_btn.add_css_class('flat')
        open_notes_btn.connect('clicked', self._on_open_notes_folder)
        notes_row.append(open_notes_btn)

        body.append(notes_row)

        body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ---- Font section ----
        font_lbl = Gtk.Label(label='FONT')
        font_lbl.add_css_class('notes-section-title')
        font_lbl.set_halign(Gtk.Align.START)
        body.append(font_lbl)

        font_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        font_row.set_valign(Gtk.Align.CENTER)

        self._font_name_lbl = Gtk.Label(label=self._current_font or 'default (Cantarell)')
        self._font_name_lbl.add_css_class('notes-context')
        self._font_name_lbl.set_halign(Gtk.Align.START)
        self._font_name_lbl.set_hexpand(True)
        self._font_name_lbl.set_ellipsize(3)
        font_row.append(self._font_name_lbl)

        choose_btn = Gtk.Button(label='choose...')
        choose_btn.add_css_class('flat')
        choose_btn.connect('clicked', self._on_choose_font)
        font_row.append(choose_btn)

        reset_btn = Gtk.Button(label='reset')
        reset_btn.add_css_class('flat')
        reset_btn.connect('clicked', self._on_reset_font)
        font_row.append(reset_btn)

        body.append(font_row)
        body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ---- Theme section ----
        section_lbl = Gtk.Label(label='THEME')
        section_lbl.add_css_class('notes-section-title')
        section_lbl.set_halign(Gtk.Align.START)
        body.append(section_lbl)

        for key, theme in THEMES.items():
            row = self._make_row(key, theme)
            self._rows[key] = row
            body.append(row)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(body)

        outer.append(scroll)
        self.set_child(outer)
        self._update_checkmarks()

    def _rebuild_folder_rows(self):
        while self._folders_box.get_first_child():
            self._folders_box.remove(self._folders_box.get_first_child())
        for folder in self._folders:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=folder)
            lbl.add_css_class('notes-context')
            lbl.set_halign(Gtk.Align.START)
            lbl.set_hexpand(True)
            lbl.set_ellipsize(3)
            lbl.set_max_width_chars(32)
            row.append(lbl)
            rm_btn = Gtk.Button()
            rm_btn.set_icon_name('list-remove-symbolic')
            rm_btn.add_css_class('flat')
            rm_btn.connect('clicked', self._on_remove_folder, folder)
            row.append(rm_btn)
            self._folders_box.append(row)

    def _on_add_folder(self, _btn):
        chooser = Gtk.FileChooserNative(
            title='Choose music folder',
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label='Add',
            cancel_label='Cancel',
        )
        chooser.set_transient_for(self.get_root())
        chooser.set_modal(True)
        chooser.connect('response', self._on_chooser_response)
        chooser.show()
        self._chooser = chooser  # keep reference alive

    def _on_chooser_response(self, chooser, response):
        if response == Gtk.ResponseType.ACCEPT:
            f = chooser.get_file()
            if f:
                path = f.get_path()
                if path and path not in self._folders:
                    self._folders.append(path)
                    self._rebuild_folder_rows()
                    self.emit('folders-changed')
        self._chooser = None

    def _on_choose_font(self, _btn):
        from gi.repository import Pango
        dialog = Gtk.FontDialog()
        dialog.set_title('Choose font')
        initial = Pango.FontDescription.from_string(self._current_font) if self._current_font else None
        dialog.choose_font(self.get_root(), initial, None, self._on_font_chosen)

    def _on_font_chosen(self, dialog, result):
        try:
            desc = dialog.choose_font_finish(result)
            if desc:
                # store full description string e.g. "Liberation Mono 11"
                font_str = desc.to_string()
                self._current_font = font_str
                self._font_name_lbl.set_text(font_str)
                self.emit('font-selected', font_str)
        except Exception:
            pass  # user cancelled

    def _on_reset_font(self, _btn):
        self._current_font = ''
        self._font_name_lbl.set_text('default (Cantarell)')
        self.emit('font-selected', '')

    def _on_open_notes_folder(self, _btn):
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(['xdg-open', str(NOTES_DIR)])

    def _on_rescan_clicked(self, _btn):
        self._rescan_btn.set_label('scanning...')
        self._rescan_btn.set_sensitive(False)
        self.emit('rescan-requested')

    def set_scan_complete(self):
        self._rescan_btn.set_label('rescan library')
        self._rescan_btn.set_sensitive(True)

    def _on_remove_folder(self, _btn, folder):
        if folder in self._folders:
            self._folders.remove(folder)
            self._rebuild_folder_rows()
            self.emit('folders-changed')

    def _make_row(self, key: str, theme: dict) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class('flat')
        btn.connect('clicked', self._on_row_clicked, key)

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_box.set_margin_top(4)
        row_box.set_margin_bottom(4)
        row_box.set_valign(Gtk.Align.CENTER)

        swatch = _ThemeSwatch(theme)
        swatch.set_valign(Gtk.Align.CENTER)
        row_box.append(swatch)

        name_lbl = Gtk.Label(label=theme['name'])
        name_lbl.add_css_class('now-playing-title')
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_hexpand(True)
        row_box.append(name_lbl)

        check = Gtk.Image.new_from_icon_name('object-select-symbolic')
        check.set_pixel_size(16)
        row_box.append(check)

        btn._check_img = check
        btn.set_child(row_box)
        return btn

    def _on_row_clicked(self, _btn, key: str):
        self._current = key
        self._update_checkmarks()
        self.emit('theme-selected', key)

    def _update_checkmarks(self):
        for key, btn in self._rows.items():
            btn._check_img.set_visible(key == self._current)
