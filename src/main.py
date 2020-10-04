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

    def do_activate(self):

        def setup_actions(window):
            """Setup menu actions."""
            about_action = Gio.SimpleAction.new('about', None)
            about_action.connect('activate', window.ui_about)
            self.add_action(about_action)

        win = self.props.active_window
        if not win:
            win = DialectWindow(
                application=self,
                title='Dialect'
            )
            setup_actions(win)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        GLib.set_application_name('Dialect')
        GLib.set_prgname('com.github.gi_lom.dialect')


def main(version):
    # Run the Application
    app = Dialect()
    return app.run(sys.argv)
