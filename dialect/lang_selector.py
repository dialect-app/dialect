# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from gi.repository import Gio, Gdk, GObject, Gtk

from dialect.define import RES_PATH
from dialect.translators import get_lang_name


@Gtk.Template(resource_path=f'{RES_PATH}/lang-selector.ui')
class DialectLangSelector(Gtk.Popover):
    __gtype_name__ = 'DialectLangSelector'
    __gsignals__ = {
        'user-selection-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ())
    }

    # Get widgets
    search = Gtk.Template.Child()
    scroll = Gtk.Template.Child()
    revealer = Gtk.Template.Child()
    recent_list = Gtk.Template.Child()
    separator = Gtk.Template.Child()
    lang_list = Gtk.Template.Child()

    # Propeties
    selected = GObject.Property(type=str)  # Key of the selected lang

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Connect popover open/close signal
        self.connect('show', self._show)
        self.connect('closed', self._closed)

        # Connect list signals
        self.recent_list.connect('row-activated', self._activated)
        self.lang_list.connect('row-activated', self._activated)

        # Setup search entry
        self.search.set_key_capture_widget(self)
        key_events = Gtk.EventControllerKey.new()
        key_events.connect('key-pressed', self._on_key_pressed)
        self.search.add_controller(key_events)
        # Connect search entry signals
        self.search.connect('changed', self._on_search)
        self.search.connect('activate', self._on_search_activate)

        self.recent_model = Gio.ListStore.new(LangObject)
        self.recent_list.bind_model(self.recent_model, self._create_lang_row)

        self.lang_model = Gio.ListStore.new(LangObject)
        self.filter = Gtk.CustomFilter()
        self.filter.set_filter_func(self._filter_func)
        fitler_model = Gtk.FilterListModel.new(self.lang_model, self.filter)
        self.lang_list.bind_model(fitler_model, self._create_lang_row)

    def get_selected(self):
        return self.get_property('selected')

    def set_selected(self, lang_code, notify=True):
        self.set_property('selected', lang_code)
        if notify:
            self.emit('user-selection-changed')

    def set_languages(self, languages):
        # Clear list
        self.lang_model.remove_all()

        # Load langs list
        for code in languages:
            self.lang_model.append(LangObject(code, get_lang_name(code)))

    def insert_recent(self, code, name):
        row_selected = (code == self.selected)
        self.recent_model.append(LangObject(code, name, row_selected))

    def clear_recent(self):
        self.recent_model.remove_all()

    def refresh_selected(self):
        for item in self.lang_model:
            item.set_property('selected', (item.code == self.selected))

    def _activated(self, _list, row):
        # Close popover
        self.popdown()
        # Set selected property
        self.set_selected(row.lang.code)

    def _show(self, _popover):
        self.search.grab_focus()

    def _closed(self, _popover):
        # Reset scroll
        vscroll = self.scroll.get_vadjustment()
        vscroll.set_value(0)
        # Clear search
        self.search.set_text('')

    def _create_lang_row(self, lang):
        return DialectLangRow(lang)

    def _filter_func(self, item):
        search = self.search.get_text()
        return bool(re.search(search, item.name, re.IGNORECASE))

    def _on_search(self, _entry):
        search = self.search.get_text()
        if search != '':
            self.revealer.set_reveal_child(False)
        else:
            self.revealer.set_reveal_child(True)

        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)

    def _on_search_activate(self, _entry):
        if self.search.get_text():
            row = self.lang_list.get_row_at_index(0)
            if row:
                self.lang_list.emit('row-activated', row)
        return Gdk.EVENT_PROPAGATE

    def _on_key_pressed(self, _controller, keyval, _keycode, _mod):
        # Close popover if ESQ key is pressed in search entry
        if keyval == Gdk.KEY_Escape:
            self.popdown()
        # Prevent search entry unfocusing when down key is pressed
        elif keyval == Gdk.KEY_Down:
            return Gdk.EVENT_STOP


class LangObject(GObject.Object):
    __gtype_name__ = 'LangObject'

    code = GObject.Property(type=str)
    name = GObject.Property(type=str)
    selected = GObject.Property(type=bool, default=False)

    def __init__(self, code, name, selected=False):
        super().__init__()

        self.set_property('code', code)
        self.set_property('name', name)
        self.set_property('selected', selected)


@Gtk.Template(resource_path=f'{RES_PATH}/lang-row.ui')
class DialectLangRow(Gtk.ListBoxRow):
    __gtype_name__ = 'DialectLangRow'

    # Widgets
    name = Gtk.Template.Child()
    selection = Gtk.Template.Child()

    def __init__(self, lang):
        super().__init__()
        self.lang = lang
        self.name.set_label(self.lang.name)

        self.lang.bind_property(
            'selected',
            self.selection,
            'visible',
            GObject.BindingFlags.SYNC_CREATE
        )
