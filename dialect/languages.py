# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gio, GObject

from dialect.define import LANGUAGES


def get_lang_name(code):
    name = LANGUAGES.get(code)
    if name:
        name = gettext(name)
    return name


class LangObject(GObject.Object):
    __gtype_name__ = "LangObject"

    code = GObject.Property(type=str)
    name = GObject.Property(type=str)
    selected = GObject.Property(type=bool, default=False)

    def __init__(self, code, name, selected=False):
        super().__init__()

        self.code = code
        self.name = name
        self.selected = selected

    def __str__(self):
        return self.code


class LanguagesListModel(GObject.GObject, Gio.ListModel):
    __gtype_name__ = "LanguagesListModel"

    def __init__(self, names_func=get_lang_name):
        super().__init__()

        self.names_func = names_func
        self.langs = []

    def __iter__(self):
        return iter(self.langs)

    def do_get_item(self, position):
        return self.langs[position]

    def do_get_item_type(self):
        return LangObject

    def do_get_n_items(self):
        return len(self.langs)

    def set_langs(self, langs, auto=False):
        removed = len(self.langs)
        self.langs.clear()

        if auto:
            self.langs.append(LangObject("auto", _("Auto")))

        for code in langs:
            self.langs.append(LangObject(code, self.names_func(code)))

        self.items_changed(0, removed, len(self.langs))

    def set_selected(self, code):
        for item in self.langs:
            item.props.selected = item.code == code
