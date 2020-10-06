# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from gi.repository import Gio, GObject, Gtk, Handy

from dialect.define import RES_PATH

@Gtk.Template(resource_path=f'{RES_PATH}/lang-selector.ui')
class DialectLangSelector(Gtk.Popover):
    __gtype_name__ = 'DialectLangSelector'

    # Get widgets
    search = Gtk.Template.Child()
    scroll = Gtk.Template.Child()
    recent_list = Gtk.Template.Child()
    lang_list = Gtk.Template.Child()
    separator = Gtk.Template.Child()

    # Propeties
    selected = GObject.Property(type=str) # Key of the selected lang

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Connect popover closed signal
        self.connect('closed', self._closed)
        # Connect list signals
        self.recent_list.connect('row-activated', self._activated)
        self.lang_list.connect('row-activated', self._activated)
        # Set filter func to lang list
        self.lang_list.set_filter_func(self.filter_func, None, False)
        # Connect search entry changed signal
        self.search.connect('changed', self._update_search)

    def filter_func(self, row, _data, _notify_destroy):
        search = self.search.get_text()
        return True if re.search(search, row.name, re.IGNORECASE) else False

    def insert(self, code, name, position=-1):
        self.lang_list.insert(LangRow(code, name), position)

    def insert_recent(self, code, name, position=-1):
        self.recent_list.insert(LangRow(code, name), position)

    def clear_recent(self):
        children = self.recent_list.get_children()
        for child in children:
            self.recent_list.remove(child)

    def _activated(self, _list, row):
        # Close popover
        self.popdown()
        # Set selected property
        self.set_property('selected', row.code)

    def _closed(self, _popover):
        # Reset scroll
        vscroll = self.scroll.get_vadjustment()
        vscroll.set_value(0)

    def _update_search(self, _entry):
        search = self.search.get_text()
        if search != '':
            self.recent_list.hide()
            self.separator.hide()
        else:
            self.recent_list.show()
            self.separator.show()
        self.lang_list.invalidate_filter()


class LangRow(Gtk.ListBoxRow):

    def __init__(self, code, name, **kwargs):
        super().__init__(**kwargs)

        self.code = code
        self.name = name

        label = Gtk.Label(self.name, halign=Gtk.Align.START,
                          margin_start=8)
        self.add(label)
        self.show_all()
