# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# Copyright 2023 Libretto
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gio, GLib, GObject, Gtk

from dialect.define import APP_ID
from dialect.providers import (
    check_translator_availability,
    get_fallback_translator_name,
    TTS,
)


class Settings(Gio.Settings):
    """
    Dialect settings handler
    """

    __gsignals__ = {
        'translator-changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'tts-changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    instance = None

    def __init__(self, *args):
        super().__init__(*args)

        self._translators = self.get_child('translators')
        self._tts = self.get_child('tts')

    @staticmethod
    def new():
        """Create a new instance of Settings."""
        g_settings = Settings(APP_ID)
        return g_settings

    @staticmethod
    def get():
        """Return an active instance of Settings."""
        if Settings.instance is None:
            Settings.instance = Settings.new()
        return Settings.instance

    @property
    def translators_list(self):
        return self._translators.get_strv('list')

    @translators_list.setter
    def translators_list(self, translators):
        self._translators.set_strv('list', translators)

    @property
    def active_translator(self):
        value = self._translators.get_string('active')

        if check_translator_availability(value):
            return value

        self.active_translator = get_fallback_translator_name()
        return get_fallback_translator_name()

    @active_translator.setter
    def active_translator(self, translator):
        self._translators.set_string('active', translator)
        self.emit('translator-changed', translator)

    @property
    def window_size(self):
        value = self.get_value('window-size')
        return (value[0], value[1])

    @window_size.setter
    def window_size(self, size):
        width, height = size
        self.set_value('window-size', GLib.Variant('ai', [width, height]))

    @property
    def translate_accel(self):
        """Return the user's preferred translation shortcut."""
        value = self.translate_accel_value

        if value == 0:
            return '<Primary>Return'
        if value == 1:
            return 'Return'

        return '<Primary>Return'

    @property
    def translate_accel_value(self):
        """Return the user's preferred translation shortcut value."""
        return self.get_int('translate-accel')

    @property
    def font_size(self):
        """Return the user's preferred font size."""
        value = self.get_int('font-size')

        if value == 0:
            return int(Gtk.Settings.get_default().get_property('gtk-font-name').split()[1])
        else:
            return value

    @font_size.setter
    def font_size(self, size):
        self.set_int('font-size', size)

    @property
    def active_tts(self):
        """Return the user's preferred TTS service."""
        value = self._tts.get_string('active')

        if value != '' and value not in TTS.keys():
            value = ''
            self.active_tts = value

        return value

    @active_tts.setter
    def active_tts(self, tts):
        """Set the user's preferred TTS service."""
        self._tts.set_string('active', tts)
        self.emit('tts-changed', tts)

    @property
    def color_scheme(self):
        return self.get_string('color-scheme')

    @color_scheme.setter
    def color_scheme(self, scheme):
        self.set_string('dark-mode', scheme)

    @property
    def live_translation(self):
        return self.get_boolean('live-translation')

    @live_translation.setter
    def live_translation(self, state):
        self.set_boolean('live-translation', state)

    @property
    def sp_translation(self):
        return self.get_boolean('sp-translation')

    @sp_translation.setter
    def sp_translation(self, state):
        self.set_boolean('sp-translation', state)

    @property
    def show_pronunciation(self):
        return self.get_boolean('show-pronunciation')

    @property
    def show_pronunciation_value(self):
        return self.get_value('show-pronunciation')

    @show_pronunciation.setter
    def show_pronunciation(self, state):
        self.set_boolean('show-pronunciation', state)

    @property
    def src_auto(self):
        return self.get_boolean('src-auto')

    @src_auto.setter
    def src_auto(self, state):
        self.set_boolean('src-auto', state)
