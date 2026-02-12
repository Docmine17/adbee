# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, GLib
from .window import AdbeeWindow


class AdbeeApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version: str):
        super().__init__(
            application_id='io.github.docmine17.adbee',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.version = version
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.start_hidden = False
        
        # Load Settings
        self.settings = Gio.Settings(schema_id='io.github.docmine17.adbee')
        
        # Auto-connect action
        action = self.settings.create_action("auto-connect")
        self.add_action(action)
        
        self.add_main_option(
            "background",
            ord("b"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Start in background",
            None,
        )

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        self.start_hidden = options.contains("background")
        self.activate()
        return 0

    def do_activate(self):
        """Called when the application is activated."""
        win = self.props.active_window
        
        if not win:
            # Create window but don't show it yet
            win = AdbeeWindow(application=self)
            
            # If starting in background, just hold the app
            if self.start_hidden:
                # Reset flag so next activation (e.g. from menu) shows the window
                self.start_hidden = False
                # We don't present the window, just return.
                return

        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name='ADBee',
            application_icon='io.github.docmine17.adbee',
            developer_name='Docmine17',
            version=self.version,
            developers=['Docmine17'],
            copyright='© 2026 Docmine17',
            license_type=Gtk.License.GPL_3_0,
            website='https://github.com/Docmine17/adbee',
            issue_url='https://github.com/Docmine17/adbee/issues',
            comments='Connect Android devices via ADB WiFi using QR code',
        )
        about.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action."""
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)


def main(version: str) -> int:
    """The application's entry point."""
    app = AdbeeApplication(version)
    return app.run(sys.argv)
