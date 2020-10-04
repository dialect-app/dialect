# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

# Initial setup
import sys
import threading
from io import BytesIO

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gio, GLib, Gtk

from .define import APP_ID, RES_PATH
from .window import DialectWindow


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
        self.window.show_all()
        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        GLib.set_application_name('Dialect')
        GLib.set_prgname('com.github.gi_lom.dialect')
        self.setup_actions()

    def setup_actions(self):
        """Setup menu actions."""
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about)
        self.add_action(about_action)

    def on_about(self, action, param):
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
