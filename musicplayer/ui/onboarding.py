import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject


class OnboardingPage(Adw.NavigationPage):

    __gsignals__ = {
        'folder-chosen': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self):
        super().__init__(title='Open Reel')
        self.set_can_pop(False)
        self._build_ui()

    def _build_ui(self):
        # No per-page HeaderBar -- the window owns the header.
        clamp = Adw.Clamp()
        clamp.set_maximum_size(480)
        clamp.set_valign(Gtk.Align.CENTER)
        clamp.set_vexpand(True)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        inner.set_margin_top(64)
        inner.set_margin_bottom(64)
        inner.set_margin_start(32)
        inner.set_margin_end(32)

        title = Gtk.Label(label='[ OPEN REEL ]')
        title.add_css_class('onboarding-title')
        title.set_halign(Gtk.Align.CENTER)
        inner.append(title)

        subtitle = Gtk.Label(label='your local music library')
        subtitle.add_css_class('amber')
        subtitle.set_halign(Gtk.Align.CENTER)
        inner.append(subtitle)

        inner.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        description = Gtk.Label()
        description.set_text(
            'choose a folder and your music will be ready to browse.\n'
            'your files are never moved, renamed, or modified.'
        )
        description.add_css_class('onboarding-subtitle')
        description.set_justify(Gtk.Justification.CENTER)
        description.set_halign(Gtk.Align.CENTER)
        inner.append(description)

        choose_button = Gtk.Button(label='choose music folder')
        choose_button.add_css_class('suggested-action')
        choose_button.set_halign(Gtk.Align.CENTER)
        choose_button.connect('clicked', self._on_choose_clicked)
        inner.append(choose_button)

        note = Gtk.Label(label='flac  mp3  ogg  opus  m4a  wav  aac')
        note.add_css_class('onboarding-note')
        note.set_halign(Gtk.Align.CENTER)
        inner.append(note)

        clamp.set_child(inner)
        self.set_child(clamp)

    def _on_choose_clicked(self, _button):
        dialog = Gtk.FileDialog()
        dialog.set_title('Choose your music folder')
        dialog.select_folder(
            parent=self.get_root(),
            cancellable=None,
            callback=self._on_dialog_response,
        )

    def _on_dialog_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.emit('folder-chosen', folder.get_path())
        except Exception:
            pass
