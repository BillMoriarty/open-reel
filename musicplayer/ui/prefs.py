import math
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

from musicplayer.themes import THEMES


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
        'theme-selected': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, current_theme_key: str):
        super().__init__()
        self.set_title('Appearance')
        self.set_content_width(340)
        self.set_content_height(280)
        self._current = current_theme_key
        self._rows = {}
        self._build_ui()

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
