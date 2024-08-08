# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Callable

from gi.repository import Gio, GObject

from dialect.define import LANGUAGES


def get_lang_name(code: str) -> str | None:
    name = LANGUAGES.get(code)
    if name:
        name = gettext(name)
    return name


class LangObject(GObject.Object):
    __gtype_name__ = "LangObject"

    code: str = GObject.Property(type=str)  # type: ignore
    name: str = GObject.Property(type=str)  # type: ignore
    selected: bool = GObject.Property(type=bool, default=False)  # type: ignore

    def __init__(self, code: str, name: str, selected=False):
        super().__init__()

        self.code = code
        self.name = name
        self.selected = selected

    def __str__(self) -> str:
        return self.code


class LanguagesListModel(GObject.GObject, Gio.ListModel):
    __gtype_name__ = "LanguagesListModel"

    def __init__(self, names_func: Callable[[str], str | None] = get_lang_name):
        super().__init__()

        self.names_func = names_func
        self.langs: list[LangObject] = []

    def __iter__(self):
        return iter(self.langs)

    def do_get_item(self, position: int) -> LangObject:
        return self.langs[position]

    def do_get_item_type(self):
        return LangObject

    def do_get_n_items(self) -> int:
        return len(self.langs)

    def set_langs(self, langs: list[str], auto=False):
        removed = len(self.langs)
        self.langs.clear()

        if auto:
            self.langs.append(LangObject("auto", _("Auto")))

        for code in langs:
            self.langs.append(LangObject(code, self.names_func(code) or code))

        self.items_changed(0, removed, len(self.langs))

    def set_selected(self, code: str):
        for item in self.langs:
            item.props.selected = item.code == code
