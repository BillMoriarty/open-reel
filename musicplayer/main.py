import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Adw, Gdk, Gio

from musicplayer.styles import get_css
from musicplayer.themes import get_theme, DEFAULT_THEME
from musicplayer import config as config_module
from musicplayer.ui.window import MainWindow


class MusicPlayerApp(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id='com.openreel.app',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._css_provider  = None
        self._font_provider = None
        self._window        = None
        self.connect('activate', self._on_activate)

    def apply_theme(self, theme_key: str):
        theme = get_theme(theme_key)
        self._css_provider.load_from_data(get_css(theme).encode('utf-8'))
        scheme = (Adw.ColorScheme.FORCE_DARK
                  if theme.get('dark', True)
                  else Adw.ColorScheme.FORCE_LIGHT)
        Adw.StyleManager.get_default().set_color_scheme(scheme)

    def apply_font(self, font_str: str):
        if font_str:
            from gi.repository import Pango
            desc    = Pango.FontDescription.from_string(font_str)
            family  = desc.get_family()
            size_pt = desc.get_size() / Pango.SCALE if desc.get_size() > 0 else 0
            weight  = desc.get_weight()   # numeric e.g. 400, 700
            style   = desc.get_style()    # Pango.Style enum

            css_style  = {
                Pango.Style.ITALIC:  'italic',
                Pango.Style.OBLIQUE: 'oblique',
            }.get(style, 'normal')

            parts = [f'font-family: "{family}";',
                     f'font-style: {css_style};',
                     f'font-weight: {int(weight)};']
            if size_pt > 0:
                parts.append(f'font-size: {size_pt}pt;')
            css = '* {{ {props} }}'.format(props=' '.join(parts))
        else:
            css = ''
        self._font_provider.load_from_data(css.encode('utf-8'))

    def _on_activate(self, _app):
        cfg       = config_module.load_config()
        theme_key = cfg.get('theme', DEFAULT_THEME)
        theme     = get_theme(theme_key)

        scheme = (Adw.ColorScheme.FORCE_DARK
                  if theme.get('dark', True)
                  else Adw.ColorScheme.FORCE_LIGHT)
        Adw.StyleManager.get_default().set_color_scheme(scheme)

        self._css_provider = Gtk.CssProvider()
        self._css_provider.load_from_data(get_css(theme).encode('utf-8'))
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            self._css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Separate provider for font overrides -- slightly higher priority
        self._font_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display,
            self._font_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )
        saved_font = cfg.get('font', '')
        if saved_font:
            self.apply_font(saved_font)

        self._window = MainWindow(application=self, initial_theme=theme_key)
        self._window.present()

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action('app.quit', ['<Ctrl>q', '<Ctrl>w'])
