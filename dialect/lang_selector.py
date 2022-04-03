# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from gi.repository import Gio, GObject, Gtk

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

        # Connect popover closed signal
        self.connect('closed', self._closed)
        # Connect list signals
        self.recent_list.connect('activate', self._activated)
        self.lang_list.connect('activate', self._activated)
        # Connect search entry changed signal
        self.search.connect('changed', self._update_search)

        self.factory = Gtk.BuilderListItemFactory.new_from_resource(
            None, f'{RES_PATH}/lang-row.ui'
        )

        self.recent_model = Gio.ListStore.new(LangObject)
        selection_model = Gtk.SingleSelection.new(self.recent_model)
        selection_model.set_autoselect(False)
        self.recent_list.set_model(selection_model)
        self.recent_list.set_factory(self.factory)

        self.lang_model = Gio.ListStore.new(LangObject)
        self.filter = Gtk.CustomFilter()
        self.filter.set_filter_func(self._filter_func)
        fitler_model = Gtk.FilterListModel.new(self.lang_model, self.filter)
        selection_model = Gtk.SingleSelection.new(fitler_model)
        selection_model.set_autoselect(False)
        self.lang_list.set_model(selection_model)
        self.lang_list.set_factory(self.factory)

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

    def _activated(self, list_view, index):
        # Close popover
        self.popdown()
        model = list_view.get_model()
        lang = model.get_selected_item()
        # Set selected property
        self.set_selected(lang.code)

    def _closed(self, _popover):
        # Reset scroll
        vscroll = self.scroll.get_vadjustment()
        vscroll.set_value(0)
        # Clear search
        self.search.set_text('')

    def _filter_func(self, item):
        search = self.search.get_text()
        return bool(re.search(search, item.name, re.IGNORECASE))

    def _update_search(self, _entry):
        search = self.search.get_text()
        if search != '':
            self.revealer.set_reveal_child(False)
        else:
            self.revealer.set_reveal_child(True)

        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)


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
