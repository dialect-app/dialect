# Copyright 2020 gi-lom
# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

# Initial setup
import sys
from gettext import gettext as _

import gi
gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
gi.require_version('Adw', '1')
gi.require_version('Soup', '3.0')

from gi.repository import Adw, Gio, GLib, Gst, Gtk

from dialect.define import APP_ID, RES_PATH, VERSION
from dialect.preferences import DialectPreferencesWindow
from dialect.settings import Settings
from dialect.window import DialectWindow


class Dialect(Adw.Application):
    def __init__(self):
        Adw.Application.__init__(
            self,
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.set_resource_base_path(RES_PATH)

        # App window
        self.window = None
        self.launch_text = ''
        self.launch_langs = {}

        # Add command line options
        self.add_main_option('text', b't', GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, 'Text to translate', None)
        self.add_main_option('src', b's', GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, 'Source lang code', None)
        self.add_main_option('dest', b'd', GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, 'Destination lang code', None)

        self.setup_actions()

    def do_activate(self):
        self.window = self.props.active_window

        if not self.window:
            width, height = Settings.get().window_size
            self.window = DialectWindow(
                application=self,
                # Translators: Do not translate the app name!
                title=_('Dialect'),
                default_height=height,
                default_width=width,
                text=self.launch_text,
                langs=self.launch_langs
            )

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()
        text = ''
        langs = {
            'src': None,
            'dest': None
        }

        if 'text' in options:
            text = options['text']
        if 'src' in options:
            langs['src'] = options['src']
        if 'dest' in options:
            langs['dest'] = options['dest']

        if self.window is not None:
            self.window.translate(text, langs['src'], langs['dest'])
        else:
            self.launch_text = text
            self.launch_langs = langs

        self.activate()
        return 0

    def do_startup(self):
        Adw.Application.do_startup(self)

        Gst.init(None)  # Init Gst

    def setup_actions(self):
        """ Setup menu actions """

        pronunciation = Gio.SimpleAction.new_stateful(
            'pronunciation', None, Settings.get().show_pronunciation_value
        )
        pronunciation.connect('change-state', self._on_pronunciation)
        self.add_action(pronunciation)

        preferences = Gio.SimpleAction.new('preferences', None)
        preferences.connect('activate', self._on_preferences)
        self.add_action(preferences)

        about = Gio.SimpleAction.new('about', None)
        about.connect('activate', self._on_about)
        self.add_action(about)

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self._on_quit)
        self.add_action(quit_action)

        self.set_accels_for_action('app.pronunciation', ['<Primary>P'])
        self.set_accels_for_action('app.preferences', ['<Primary>comma'])
        self.set_accels_for_action('app.quit', ['<Primary>Q'])

        self.set_accels_for_action('win.back', ['<Alt>Left'])
        self.set_accels_for_action('win.forward', ['<Alt>Right'])
        self.set_accels_for_action('win.switch', ['<Primary>S'])
        self.set_accels_for_action('win.clear', ['<Primary>D'])
        self.set_accels_for_action('win.paste', ['<Primary><Shift>V'])
        self.set_accels_for_action('win.copy', ['<Primary><Shift>C'])
        self.set_accels_for_action('win.listen-dest', ['<Primary>L'])
        self.set_accels_for_action('win.listen-src', ['<Primary><Shift>L'])
        self.set_accels_for_action('win.show-help-overlay', ['<Primary>question'])

    def _on_pronunciation(self, action, value):
        """ Update show pronunciation setting """
        action.set_state(value)
        Settings.get().show_pronunciation = value

        # Update UI
        if self.window.trans_src_pron is not None:
            self.window.src_pron_revealer.set_reveal_child(value)
        if self.window.trans_dest_pron is not None:
            self.window.dest_pron_revealer.set_reveal_child(value)

    def _on_preferences(self, _action, _param):
        """ Show preferences window """
        window = DialectPreferencesWindow(self.window)
        window.set_transient_for(self.window)
        window.present()

    def _on_about(self, _action, _param):
        """ Show about dialog """
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/about.ui')
        about = builder.get_object('about')
        about.set_authors(["Mufeed Ali", "Rafael Mardojai CM"])
        about.set_transient_for(self.window)
        about.set_logo_icon_name(APP_ID)
        about.set_version(VERSION)
        about.present()

    def _on_quit(self, _action, _param):
        self.quit()


def main():
    # Run the Application
    app = Dialect()
    return app.run(sys.argv)
