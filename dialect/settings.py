# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# Copyright 2023 Libretto
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Literal

from gi.repository import Gio, GLib, GObject

from dialect.define import APP_ID
from dialect.providers import (
    TTS,
    check_translator_availability,
    get_fallback_translator_name,
)


class Settings(Gio.Settings):
    """
    Dialect settings handler
    """

    instance = None

    def __init__(self, *args):
        super().__init__(*args)

        self._translators = self.get_child("translators")
        self._tts = self.get_child("tts")

    @staticmethod
    def new() -> Settings:
        """Create a new instance of Settings."""
        g_settings = Settings(APP_ID)
        return g_settings

    @staticmethod
    def get() -> Settings:
        """Return an active instance of Settings."""
        if Settings.instance is None:
            Settings.instance = Settings.new()
        return Settings.instance

    @GObject.Signal(flags=GObject.SignalFlags.DETAILED, arg_types=(str, str))
    def provider_changed(self, name: str): ...

    @property
    def translators_list(self) -> list[str]:
        return self._translators.get_strv("list")

    @translators_list.setter
    def translators_list(self, translators: list[str]):
        self._translators.set_strv("list", translators)

    @property
    def active_translator(self) -> str:
        value = self._translators.get_string("active")

        if check_translator_availability(value):
            return value

        self.active_translator = get_fallback_translator_name()
        return get_fallback_translator_name()

    @active_translator.setter
    def active_translator(self, translator: str):
        self._translators.set_string("active", translator)
        self.emit("provider-changed::translator", "translator", translator)

    @property
    def window_size(self) -> tuple[int, int]:
        value = self.get_value("window-size")
        return (value[0], value[1])

    @window_size.setter
    def window_size(self, size: tuple[int, int]):
        width, height = size
        self.set_value("window-size", GLib.Variant("ai", [width, height]))

    @property
    def translate_accel(self) -> str:
        """Return the user's preferred translation shortcut."""
        value = self.translate_accel_value

        if value == 0:
            return "<Primary>Return"
        if value == 1:
            return "Return"

        return "<Primary>Return"

    @property
    def translate_accel_value(self) -> int:
        """Return the user's preferred translation shortcut value."""
        return self.get_int("translate-accel")

    @property
    def custom_default_font_size(self) -> bool:
        """Return whether the user wants a custom default font size."""
        return self.get_boolean("custom-default-font-size")

    @custom_default_font_size.setter
    def custom_default_font_size(self, enabled: bool):
        self.set_boolean("custom-default-font-size", enabled)

    @property
    def default_font_size(self) -> int:
        """Return the user's preferred default font size."""
        return self.get_int("default-font-size")

    @default_font_size.setter
    def default_font_size(self, size: int):
        self.set_int("default-font-size", size)

    @property
    def system_font_size(self) -> int:
        """Return the systems's default font size."""
        from gi.repository import Gtk

        try:
            gtk_font_name = Gtk.Settings.get_default().get_property("gtk-font-name").split(" ")  # type: ignore
            return int(gtk_font_name[-1])
        except Exception:
            return 11

    @property
    def active_tts(self) -> str:
        """Return the user's preferred TTS service."""
        value = self._tts.get_string("active")

        if value != "" and value not in TTS.keys():
            value = ""
            self.active_tts = value

        return value

    @active_tts.setter
    def active_tts(self, tts: str):
        """Set the user's preferred TTS service."""
        self._tts.set_string("active", tts)
        self.emit("provider-changed::tts", "tts", tts)

    @property
    def color_scheme(self) -> str:
        return self.get_string("color-scheme")

    @color_scheme.setter
    def color_scheme(self, scheme: Literal["auto", "light", "dark"]):
        self.set_string("color-scheme", scheme)

    @property
    def live_translation(self) -> bool:
        return self.get_boolean("live-translation")

    @live_translation.setter
    def live_translation(self, state: bool):
        self.set_boolean("live-translation", state)

    @property
    def sp_translation(self) -> bool:
        return self.get_boolean("sp-translation")

    @sp_translation.setter
    def sp_translation(self, state: bool):
        self.set_boolean("sp-translation", state)

    @property
    def show_pronunciation(self) -> bool:
        return self.get_boolean("show-pronunciation")

    @property
    def show_pronunciation_value(self) -> GLib.Variant:
        return self.get_value("show-pronunciation")

    @show_pronunciation.setter
    def show_pronunciation(self, state: bool):
        self.set_boolean("show-pronunciation", state)

    @property
    def src_auto(self) -> bool:
        return self.get_boolean("src-auto")

    @src_auto.setter
    def src_auto(self, state: bool):
        self.set_boolean("src-auto", state)
