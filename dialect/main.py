# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

# Initial setup
import asyncio
import logging
import sys

import gi
from gi.events import GLibEventLoopPolicy

try:
    gi.require_version("Gdk", "4.0")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gst", "1.0")
    gi.require_version("Adw", "1")
    gi.require_version("Secret", "1")
    gi.require_version("Soup", "3.0")
    gi.require_version("Spelling", "1")
    gi.require_version("GtkSource", "5")

    from gi.repository import Adw, Gio, GLib, Gst
except ImportError or ValueError:
    logging.error("Error: GObject dependencies not met.")

from dialect.define import APP_ID, RES_PATH, VERSION
from dialect.preferences import DialectPreferencesDialog
from dialect.settings import Settings
from dialect.window import DialectWindow


class Dialect(Adw.Application):
    def __init__(self):
        Adw.Application.__init__(self, application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.set_resource_base_path(RES_PATH)

        # App window
        self.window: DialectWindow | None = None
        # CLI
        self.argv: dict[str, str] = {}
        self._signal_handler: int | None = None

        # Add command line options
        self.add_main_option(
            "selection",
            ord("n"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Translate text from the primary clipboard",
            None,
        )
        self.add_main_option("text", ord("t"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "Text to translate", None)
        self.add_main_option("src", ord("s"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "Source lang code", None)
        self.add_main_option(
            "dest", ord("d"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "Destination lang code", None
        )

        self.setup_actions()

    def do_activate(self):
        def on_translator_loading(_win, _pspec):
            if self.window and not self.window.translator_loading:
                # Remove signal handler
                if self._signal_handler:
                    self.window.disconnect(self._signal_handler)
                # Process CLI args
                self.process_command_line()

        self.window = self.props.active_window  # type: ignore

        if not self.window:
            width, height = Settings.get().window_size
            self.window = DialectWindow(
                application=self,
                # Translators: Do not translate the app name!
                title=_("Dialect"),
                default_height=height,
                default_width=width,
            )

        # Decide when to process command line args
        if self.window.translator_loading:
            # Wait until translator is loaded
            self._signal_handler = self.window.connect("notify::translator-loading", on_translator_loading)
        else:
            self.process_command_line()

        self.window.present()

    def do_command_line(self, command_line: Gio.ApplicationCommandLine):
        options = command_line.get_options_dict()

        # Save CLI args values
        self.argv = options.end().unpack()

        self.activate()

        return 0

    def do_startup(self):
        Adw.Application.do_startup(self)

        Gst.init(None)  # Init Gst

    def process_command_line(self):
        if not self.argv:
            return

        text = ""
        langs: dict[str, str | None] = {"src": None, "dest": None}
        selection = "selection" in self.argv

        if "text" in self.argv:
            text = self.argv["text"]
        if "src" in self.argv:
            langs["src"] = self.argv["src"]
        if "dest" in self.argv:
            langs["dest"] = self.argv["dest"]

        if self.window is not None:
            if not text and selection:
                self.window.queue_selection_translation(langs["src"], langs["dest"])
            elif text:
                self.window.translate(text, langs["src"], langs["dest"])

        # Clean CLI args
        self.argv = {}

    def setup_actions(self):
        """Setup menu actions"""

        pronunciation = Gio.SimpleAction.new_stateful("pronunciation", None, Settings.get().show_pronunciation_value)
        pronunciation.connect("change-state", self._on_pronunciation)
        self.add_action(pronunciation)

        preferences = Gio.SimpleAction(name="preferences")
        preferences.connect("activate", self._on_preferences)
        self.add_action(preferences)

        about = Gio.SimpleAction(name="about")
        about.connect("activate", self._on_about)
        self.add_action(about)

        quit_action = Gio.SimpleAction(name="quit")
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

        self.set_accels_for_action("app.pronunciation", ["<Primary>P"])
        self.set_accels_for_action("app.preferences", ["<Primary>comma"])
        self.set_accels_for_action("app.quit", ["<Primary>Q"])

        self.set_accels_for_action("win.back", ["<Alt>Left"])
        self.set_accels_for_action("win.forward", ["<Alt>Right"])
        self.set_accels_for_action("win.switch", ["<Primary>S"])
        self.set_accels_for_action("win.from", ["<Primary>F"])
        self.set_accels_for_action("win.to", ["<Primary>T"])
        self.set_accels_for_action("win.clear", ["<Primary>D"])
        self.set_accels_for_action("win.font-size-inc", ["<Primary>plus", "<Primary>KP_Add"])
        self.set_accels_for_action("win.font-size-dec", ["<Primary>minus", "<Primary>KP_Subtract"])
        self.set_accels_for_action("win.paste", ["<Primary><Shift>V"])
        self.set_accels_for_action("win.copy", ["<Primary><Shift>C"])
        self.set_accels_for_action("win.listen-dest", ["<Primary>L"])
        self.set_accels_for_action("win.listen-src", ["<Primary><Shift>L"])
        self.set_accels_for_action("win.show-help-overlay", ["<Primary>question"])

    def _on_pronunciation(self, action: Gio.SimpleAction, value: GLib.Variant):
        """Update show pronunciation setting"""
        action.props.state = value
        Settings.get().show_pronunciation = value  # type: ignore

        # Update UI
        if self.window:
            self.window._check_pronunciation()

    def _on_preferences(self, _action, _param):
        """Show preferences window"""
        if self.window:
            window = DialectPreferencesDialog(self.window)
            window.present(self.window)

    def _on_about(self, _action, _param):
        """Show about dialog"""
        about = Adw.AboutDialog.new_from_appdata(f"{RES_PATH}/appdata.xml", VERSION)
        about.props.version = VERSION  # For development version
        about.props.comments = _("A translation app for GNOME.")
        about.props.copyright = _("Copyright 2020–⁠2024 The Dialect Authors")
        about.props.developers = ["Mufeed Ali", "Rafael Mardojai CM http://rafaelmardojai.com", "Libretto"]
        about.props.translator_credits = _("translator-credits")
        about.add_link(_("Donate"), "https://opencollective.com/dialect")

        about.present(self.window)

    def _on_quit(self, _action, _param):
        self.quit()


def main():
    # Set the asyncio event loop policy from PyGObject
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    # Run the Application
    app = Dialect()
    return app.run(sys.argv)
