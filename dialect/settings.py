# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gio, GLib

from dialect.define import APP_ID
from dialect.translators import (
    check_backend_availability,
    get_fallback_backend_name,
    TRANSLATORS
)
from dialect.tts import TTS


class Settings(Gio.Settings):
    """
    Dialect settings handler
    """

    instance = None
    translator = None

    def __init__(self):
        Gio.Settings.__init__(self)

    @staticmethod
    def new():
        """Create a new instance of Settings."""
        g_settings = Gio.Settings.new(APP_ID)
        g_settings.__class__ = Settings
        g_settings.init_translators_settings()
        return g_settings

    @staticmethod
    def get():
        """Return an active instance of Settings."""
        if Settings.instance is None:
            Settings.instance = Settings.new()
        return Settings.instance

    def init_translators_settings(self):
        """Intialize translators settings with its default values."""
        self.translators_list = list(TRANSLATORS.keys())
        for name, instance in TRANSLATORS.items():
            settings = self.get_translator_settings(name)
            if not settings.get_boolean('init'):
                settings.set_strv('src-langs', instance.src_langs)
                settings.set_strv('dest-langs', instance.dest_langs)
                settings.set_string('instance-url', instance.instance_url)
                settings.set_string('api-key', instance.api_key)
                settings.set_boolean('init', True)

    @property
    def translators_list(self):
        return self.get_child('translators').get_strv('list')

    @translators_list.setter
    def translators_list(self, translators):
        self.get_child('translators').set_strv('list', translators)

    @property
    def active_translator(self):
        value = self.get_child('translators').get_string('active')

        if check_backend_availability(value):
            return value

        self.active_translator = get_fallback_backend_name()
        return get_fallback_backend_name()

    @active_translator.setter
    def active_translator(self, translator):
        self.get_child('translators').set_string('active', translator)
        self.translator = None

    def get_translator_settings(self, translator=None):
        def on_changed(_settings, key):
            self.emit('changed', 'translator-' + key)

        def get_settings(name):
            path = self.get_child('translators').get_property('path')
            if not path.endswith('/'):
                path += '/'
            path += name + '/'
            settings = Gio.Settings(APP_ID + '.translator', path)
            settings.connect('changed', on_changed)
            return settings

        if translator is not None:
            translator = get_settings(translator)
            return translator
        if self.translator is None:
            self.translator = get_settings(self.active_translator)
            self.translator.delay()
        return self.translator

    def save_translator_settings(self):
        if self.translator is not None:
            self.translator.apply()

    @property
    def src_langs(self):
        return self.get_translator_settings().get_strv('src-langs')

    @src_langs.setter
    def src_langs(self, src_langs):
        self.get_translator_settings().set_strv('src-langs', src_langs)

    def reset_src_langs(self):
        self.src_langs = TRANSLATORS[self.active_translator].src_langs

    @property
    def dest_langs(self):
        return self.get_translator_settings().get_strv('dest-langs')

    @dest_langs.setter
    def dest_langs(self, dest_langs):
        self.get_translator_settings().set_strv('dest-langs', dest_langs)

    def reset_dest_langs(self):
        self.dest_langs = TRANSLATORS[self.active_translator].dest_langs

    @property
    def instance_url(self):
        return self.get_translator_settings().get_string('instance-url')

    @instance_url.setter
    def instance_url(self, url):
        self.get_translator_settings().set_string('instance-url', url)
        self.save_translator_settings()

    def reset_instance_url(self):
        self.instance_url = TRANSLATORS[self.active_translator].instance_url

    @property
    def api_key(self):
        return self.get_translator_settings().get_string('api-key')

    @api_key.setter
    def api_key(self, api_key):
        self.get_translator_settings().set_string('api-key', api_key)
        self.save_translator_settings()

    def reset_api_key(self):
        self.api_key = TRANSLATORS[self.active_translator].api_key

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
    def active_tts(self):
        """Return the user's preferred TTS service."""
        value = self.get_child('tts').get_string('active')

        if value != '' and value not in TTS.keys():
            value = ''
            self.active_tts = value

        return value

    @active_tts.setter
    def active_tts(self, tts):
        """Set the user's preferred TTS service."""
        self.get_child('tts').set_string('active', tts)

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
