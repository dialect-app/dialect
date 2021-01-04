# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

# Initial setup
import sys
from gettext import gettext as _

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Handy', '1')

from gi.repository import Gdk, Gio, GLib, Gtk, Gst, Handy

from dialect.define import APP_ID, RES_PATH
from dialect.window import DialectWindow
from dialect.preferences import DialectPreferencesWindow


class Dialect(Gtk.Application):
    def __init__(self, version):
        Gtk.Application.__init__(
            self,
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )

        # App window
        self.version = version
        self.window = None
        self.launch_text = ''
        self.settings = Gio.Settings.new(APP_ID)

        # Add --text command line option
        self.add_main_option('text', b't', GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, 'Text to translate', None)

    def do_activate(self):
        self.window = self.props.active_window
        if not self.window:
            self.window = DialectWindow(
                application=self,
                # Translators: Do not translate the app name!
                title=_('Dialect'),
                text=self.launch_text,
                settings=self.settings
            )
        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if 'text' in options:
            if self.window is not None:
                self.window.translate(options['text'])
            else:
                self.launch_text = options['text']

        self.activate()
        return 0

    def do_startup(self):
        Gtk.Application.do_startup(self)
        GLib.set_application_name(_('Dialect'))
        GLib.set_prgname('com.github.gi_lom.dialect')
        self.setup_actions()

        Handy.init()  # Init Handy
        Gst.init(None)  # Init Gst

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource(f'{RES_PATH}/style.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def setup_actions(self):
        """ Setup menu actions """

        pronunciation_action = Gio.SimpleAction.new_stateful(
            'pronunciation', None, self.settings.get_value('show-pronunciation')
        )
        pronunciation_action.connect('change-state', self.on_pronunciation)
        self.add_action(pronunciation_action)

        preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect('activate', self.on_preferences)
        self.set_accels_for_action('app.preferences', ['<Primary>comma'])
        self.add_action(preferences_action)

        shortcuts_action = Gio.SimpleAction.new('shortcuts', None)
        shortcuts_action.connect('activate', self.on_shortcuts)
        self.add_action(shortcuts_action)

        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit)
        self.set_accels_for_action('app.quit', ['<Primary>Q'])
        self.add_action(quit_action)

    def on_pronunciation(self, action, value):
        """ Update show pronunciation setting """
        action.set_state(value)
        self.settings.set_boolean('show-pronunciation', value)

        # Update UI
        if self.window.trans_pronunciation is not None:
            self.window.pronunciation_revealer.set_reveal_child(value)

    def on_preferences(self, _action, _param):
        """ Show preferences window """
        window = DialectPreferencesWindow(settings=self.settings)
        window.set_transient_for(self.window)
        window.present()

    def on_shortcuts(self, _action, _param):
        """Launch the Keyboard Shortcuts window."""
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/shortcuts-window.ui')
        translate_shortcut = builder.get_object('translate_shortcut')
        translate_shortcut.set_visible(not self.settings.get_boolean('live-translation'))
        if self.settings.get_value('translate-accel'):
            translate_shortcut.set_property('accelerator', 'Return')
        else:
            translate_shortcut.set_property('accelerator', '<Primary>Return')
        shortcuts_window = builder.get_object('shortcuts')
        shortcuts_window.set_transient_for(self.window)
        shortcuts_window.show()

    def on_about(self, _action, _param):
        """ Show about dialog """
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/about.ui')
        about = builder.get_object('about')
        about.set_transient_for(self.window)
        about.set_logo_icon_name(APP_ID)
        about.set_version(self.version)
        about.connect('response', lambda dialog, response: dialog.destroy())
        about.present()

    def on_quit(self, _action, _param):
        self.quit()


def main(version):
    # Run the Application
    app = Dialect(version)
    return app.run(sys.argv)
