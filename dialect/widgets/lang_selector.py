# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from gi.repository import Adw, Gdk, GObject, Gtk

from dialect.define import RES_PATH
from dialect.languages import LangObject, LanguagesListModel


@Gtk.Template(resource_path=f"{RES_PATH}/widgets/lang_selector.ui")
class LangSelector(Adw.Bin):
    __gtype_name__ = "LangSelector"

    # Properties
    selected: str = GObject.Property(type=str)  # type: ignore

    # Child Widgets
    button: Gtk.MenuButton = Gtk.Template.Child()  # type: ignore
    label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    insight: Gtk.Label = Gtk.Template.Child()  # type: ignore
    popover: Gtk.Popover = Gtk.Template.Child()  # type: ignore
    search: Gtk.SearchEntry = Gtk.Template.Child()  # type: ignore
    scroll: Gtk.ScrolledWindow = Gtk.Template.Child()  # type: ignore
    revealer: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    recent_list: Gtk.ListBox = Gtk.Template.Child()  # type: ignore
    separator: Gtk.Separator = Gtk.Template.Child()  # type: ignore
    lang_list: Gtk.ListBox = Gtk.Template.Child()  # type: ignore

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.model: LanguagesListModel | None = None
        self.recent_model: LanguagesListModel | None = None

        # Setup search entry
        self.search.set_key_capture_widget(self.popover)
        key_events = Gtk.EventControllerKey()
        key_events.connect("key-pressed", self._on_key_pressed)
        self.search.add_controller(key_events)

    @GObject.Signal()
    def user_selection_changed(self): ...

    def bind_models(self, langs: LanguagesListModel, recent: LanguagesListModel):
        self.model = langs
        self.recent_model = recent

        self.recent_model.connect("items-changed", self._on_recent_changed)

        self.filter = Gtk.CustomFilter()
        self.filter.set_filter_func(self._filter_langs)
        sorter = Gtk.CustomSorter()
        sorter.set_sort_func(self._sort_langs)
        sorted_model = Gtk.SortListModel(model=self.model, sorter=sorter)
        filter_model = Gtk.FilterListModel(model=sorted_model, filter=self.filter)
        self.lang_list.bind_model(filter_model, self._create_lang_row)

        self.recent_list.bind_model(self.recent_model, self._create_lang_row)

    def set_insight(self, code: str):
        if self.selected == "auto":
            self.insight.props.label = f"({self._get_lang_name(code)})"

    def _get_lang_name(self, code: str) -> str:
        if self.model:
            return self.model.names_func(code) or code
        return code

    def _on_recent_changed(self, _model, _position: int, _removed: int, _added: int):
        if self.recent_model:
            self.recent_model.set_selected(self.selected)

    @Gtk.Template.Callback()
    def _on_selected_changed(self, _self, _pspec):
        """Called on self::notify::selected signal"""

        if self.model is not None:
            self.model.set_selected(self.selected)

            if self.selected == "auto":
                self.label.props.label = _("Auto")
            else:
                self.label.props.label = self._get_lang_name(self.selected)

            self.insight.props.label = ""

    @Gtk.Template.Callback()
    def _activated(self, _list, row: "LangRow"):
        """Called on self.(recent_list, lang_list)::row-activated signal"""
        # Close popover
        self.popover.popdown()
        # Set selected property
        self.selected = row.lang.code
        self.emit("user-selection-changed")

    @Gtk.Template.Callback()
    def _popover_show(self, _popover):
        """Called on self.popover::show signal"""
        self.search.grab_focus()

    @Gtk.Template.Callback()
    def _popover_closed(self, _popover):
        """Called on self.popover::closed signal"""
        # Reset scroll
        vscroll = self.scroll.get_vadjustment()
        vscroll.props.value = 0
        # Clear search
        self.search.props.text = ""

    def _create_lang_row(self, lang: LangObject):
        return LangRow(lang)

    def _filter_langs(self, item):
        search = self.search.get_text()
        return bool(re.search(search, item.name, re.IGNORECASE))

    def _sort_langs(self, lang_a, lang_b, _data):
        a = lang_a.name.lower()
        b = lang_b.name.lower()
        return (a > b) - (a < b)

    @Gtk.Template.Callback()
    def _on_search(self, _entry):
        """Called on self.search::changed signal"""
        if self.search.props.text != "":
            self.revealer.props.reveal_child = False
        else:
            self.revealer.props.reveal_child = True

        self.filter.emit("changed", Gtk.FilterChange.DIFFERENT)

    @Gtk.Template.Callback()
    def _on_search_activate(self, _entry):
        """Called on self.search::activate signal"""
        if self.search.props.text:
            row = self.lang_list.get_row_at_index(0)
            if row:
                self.lang_list.emit("row-activated", row)
        return Gdk.EVENT_PROPAGATE

    def _on_key_pressed(self, _ctrl, keyval: int, _keycode: int, _mod: Gdk.ModifierType):
        # Close popover if ESQ key is pressed in search entry
        if keyval == Gdk.KEY_Escape:
            self.popover.popdown()
        # Prevent search entry unfocusing when down key is pressed
        elif keyval == Gdk.KEY_Down:
            return Gdk.EVENT_STOP


@Gtk.Template(resource_path=f"{RES_PATH}/widgets/lang_row.ui")
class LangRow(Gtk.ListBoxRow):
    __gtype_name__ = "LangRow"

    # Widgets
    name: Gtk.Label = Gtk.Template.Child()  # type: ignore
    selection: Gtk.Image = Gtk.Template.Child()  # type: ignore

    def __init__(self, lang: LangObject):
        super().__init__()
        self.lang = lang
        self.name.props.label = self.lang.name

        self.lang.bind_property("selected", self.selection, "visible", GObject.BindingFlags.SYNC_CREATE)
