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
            application_id='com.billmoriarty.musicplayer',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._css_provider = None
        self._window       = None
        self.connect('activate', self._on_activate)

    def apply_theme(self, theme_key: str):
        """Live-reload CSS and mascot colours with the new theme."""
        theme = get_theme(theme_key)
        self._css_provider.load_from_data(get_css(theme).encode('utf-8'))
        scheme = (Adw.ColorScheme.FORCE_DARK
                  if theme.get('dark', True)
                  else Adw.ColorScheme.FORCE_LIGHT)
        Adw.StyleManager.get_default().set_color_scheme(scheme)

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

        self._window = MainWindow(application=self, initial_theme=theme_key)
        self._window.present()

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action('app.quit', ['<Ctrl>q', '<Ctrl>w'])
