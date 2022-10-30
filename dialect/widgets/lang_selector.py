# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from gettext import gettext as _

from gi.repository import Gdk, GObject, Gtk

from dialect.define import RES_PATH
from dialect.languages import get_lang_name


@Gtk.Template(resource_path=f'{RES_PATH}/lang-selector.ui')
class LangSelector(Gtk.Widget):
    __gtype_name__ = 'LangSelector'
    __gsignals__ = {
        'user-selection-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ())
    }

    # Get widgets
    button = Gtk.Template.Child()
    label = Gtk.Template.Child()
    popover = Gtk.Template.Child()
    search = Gtk.Template.Child()
    scroll = Gtk.Template.Child()
    revealer = Gtk.Template.Child()
    recent_list = Gtk.Template.Child()
    separator = Gtk.Template.Child()
    lang_list = Gtk.Template.Child()

    # Properties
    selected = GObject.Property(type=str)  # Code of the selected lang

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.model = None
        self.recent_model = None

        self.connect('notify::selected', self._on_selected_changed)

        # Connect popover open/close signal
        self.popover.connect('show', self._show)
        self.popover.connect('closed', self._closed)

        # Connect list signals
        self.recent_list.connect('row-activated', self._activated)
        self.lang_list.connect('row-activated', self._activated)

        # Setup search entry
        self.search.set_key_capture_widget(self.popover)
        key_events = Gtk.EventControllerKey.new()
        key_events.connect('key-pressed', self._on_key_pressed)
        self.search.add_controller(key_events)
        self.search.connect('changed', self._on_search)
        self.search.connect('activate', self._on_search_activate)

    def bind_models(self, langs, recent):
        self.model = langs
        self.recent_model = recent

        self.recent_model.connect('items-changed', self._on_recent_changed)

        self.filter = Gtk.CustomFilter()
        self.filter.set_filter_func(self._filter_func)
        filter_model = Gtk.FilterListModel.new(self.model, self.filter)
        self.lang_list.bind_model(filter_model, self._create_lang_row)

        self.recent_list.bind_model(self.recent_model, self._create_lang_row)

    def set_insight(self, code):
        if self.selected == 'auto':
            self.label.props.label = f'{self.label.props.label} ({get_lang_name(code)})'

    def _on_recent_changed(self, _model, _position, _removed, _added):
        self.recent_model.set_selected(self.selected)

    def _on_selected_changed(self, _self, _pspec):
        if self.model is not None:
            self.model.set_selected(self.selected)

            if self.selected == 'auto':
                self.label.props.label = _('Auto')
            else:
                self.label.props.label = get_lang_name(self.selected)

    def _activated(self, _list, row):
        # Close popover
        self.popover.popdown()
        # Set selected property
        self.selected = row.lang.code
        self.emit('user-selection-changed')

    def _show(self, _popover):
        self.search.grab_focus()

    def _closed(self, _popover):
        # Reset scroll
        vscroll = self.scroll.get_vadjustment()
        vscroll.props.value = 0
        # Clear search
        self.search.props.text = ''

    def _create_lang_row(self, lang):
        return LangRow(lang)

    def _filter_func(self, item):
        search = self.search.get_text()
        return bool(re.search(search, item.name, re.IGNORECASE))

    def _on_search(self, _entry):
        if self.search.props.text != '':
            self.revealer.props.reveal_child = False
        else:
            self.revealer.props.reveal_child = True

        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)

    def _on_search_activate(self, _entry):
        if self.search.props.text:
            row = self.lang_list.get_row_at_index(0)
            if row:
                self.lang_list.emit('row-activated', row)
        return Gdk.EVENT_PROPAGATE

    def _on_key_pressed(self, _controller, keyval, _keycode, _mod):
        # Close popover if ESQ key is pressed in search entry
        if keyval == Gdk.KEY_Escape:
            self.popover.popdown()
        # Prevent search entry unfocusing when down key is pressed
        elif keyval == Gdk.KEY_Down:
            return Gdk.EVENT_STOP


@Gtk.Template(resource_path=f'{RES_PATH}/lang-row.ui')
class LangRow(Gtk.ListBoxRow):
    __gtype_name__ = 'LangRow'

    # Widgets
    name = Gtk.Template.Child()
    selection = Gtk.Template.Child()

    def __init__(self, lang):
        super().__init__()
        self.lang = lang
        self.name.props.label = self.lang.name

        self.lang.bind_property(
            'selected',
            self.selection,
            'visible',
            GObject.BindingFlags.SYNC_CREATE
        )
