# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

# Initial setup
import sys

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

    def __init__(self):
        Gtk.Application.__init__(self, application_id=APP_ID)

        # App window
        self.window = None

    def do_activate(self):
        self.window = self.props.active_window
        if not self.window:
            self.window = DialectWindow(
                application=self,
                title='Dialect'
            )
        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        GLib.set_application_name('Dialect')
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

        preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect('activate', self.on_preferences)
        self.add_action(preferences_action)

        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about)
        self.add_action(about_action)

    def on_preferences(self, _action, _param):
        """ Show preferences window """
        window = DialectPreferencesWindow()
        window.set_transient_for(self.window)
        window.present()

    def on_about(self, _action, _param):
        """ Show about dialog """
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/about.ui')
        about = builder.get_object('about')
        about.set_transient_for(self.window)
        about.set_logo_icon_name(APP_ID)
        about.connect('response', lambda dialog, response: dialog.destroy())
        about.present()


def main(version):
    # Run the Application
    app = Dialect()
    return app.run(sys.argv)
