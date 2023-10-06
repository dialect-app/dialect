# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import urllib.parse
from enum import Enum, Flag, auto
from typing import Callable

from gi.repository import Gio

from dialect.define import APP_ID
from dialect.languages import get_lang_name, normalize_lang_code


class ProviderCapability(Flag):
    TRANSLATION = auto()
    """ If it provides translation """
    TTS = auto()
    """ If it provides text-to-speech """
    DEFINITIONS = auto()
    """ If it provides dictionary definitions """


class ProviderFeature(Flag):
    NONE = auto()
    """ Provider has no features """
    INSTANCES = auto()
    """ If it supports changing the instance url """
    API_KEY = auto()
    """ If the api key is supported but not necessary """
    API_KEY_REQUIRED = auto()
    """ If the api key is required for the provider to work """
    DETECTION = auto()
    """ If it supports detecting text language (Auto translation) """
    MISTAKES = auto()
    """ If it supports showing translation mistakes """
    PRONUNCIATION = auto()
    """ If it supports showing translation pronunciation """
    SUGGESTIONS = auto()
    """ If it supports sending translation suggestions to the service """


class ProviderErrorCode(Enum):
    UNEXPECTED = auto()
    NETWORK = auto
    EMPTY = auto()
    API_KEY_REQUIRED = auto()
    API_KEY_INVALID = auto()
    INVALID_LANG_CODE = auto()
    BATCH_SIZE_EXCEEDED = auto()
    CHARACTERS_LIMIT_EXCEEDED = auto()
    SERVICE_LIMIT_REACHED = auto()
    TRANSLATION_FAILED = auto()
    TTS_FAILED = auto()


class ProviderError:
    """Helper error handing class to be passed between callbacks"""

    def __init__(self, code: ProviderErrorCode, message: str = '') -> None:
        self.code = code  # Serves for quick error matching
        self.message = message  # More detailed error info if needed


class Translation:
    def __init__(
        self,
        text: str,
        detected: None | str = None,
        mistakes: tuple[None | str, None | str] = (None, None),
        pronunciation: tuple[None | str, None | str] = (None, None),
    ):
        self.text = text
        self.detected = detected
        self.mistakes = mistakes
        self.pronunciation = pronunciation


class BaseProvider:
    name = ''
    """ Module name for code use, like settings storing """
    prettyname = ''
    """ Module name for UI display """
    capabilities: ProviderCapability | None = None
    """ Provider capabilities, translation, tts, etc """
    features: ProviderFeature = ProviderFeature.NONE
    """ Provider features """

    defaults = {
        'instance_url': '',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en'],
    }
    """ Default provider settings """

    def __init__(self):
        self.languages = []
        """ Languages available for translating """
        self.tts_languages = []
        """ Languages available for TTS """
        self._nonstandard_langs = {}
        """ Mapping of lang codes that differ with Dialect ones """
        self._languages_names = {}
        """ Names of languages provided by the service """

        self.chars_limit = -1
        """ Translation char limit """

        self.history = []
        """ Here we save the translation history """

        # GSettings
        self.settings = Gio.Settings(f'{APP_ID}.translator', f'/app/drey/Dialect/translators/{self.name}/')

    """
    Providers API methods
    """

    @staticmethod
    def validate_instance(url: str, on_done: Callable[[bool], None], on_fail: Callable[[ProviderError], None]):
        raise NotImplementedError()

    def validate_api_key(self, key: str, on_done: Callable[[bool], None], on_fail: Callable[[ProviderError], None]):
        raise NotImplementedError()

    def init_trans(self, on_done: Callable, on_fail: Callable[[ProviderError], None]):
        on_done()

    def init_tts(self, on_done: Callable, on_fail: Callable[[ProviderError], None]):
        on_done()

    def translate(
        self,
        text: str,
        src: str,
        dest: str,
        on_done: Callable[[Translation], None],
        on_fail: Callable[[ProviderError], None],
    ):
        raise NotImplementedError()

    def suggest(
        self,
        text: str,
        src: str,
        dest: str,
        suggestion: str,
        on_done: Callable[[bool], None],
        on_fail: Callable[[ProviderError], None],
    ):
        raise NotImplementedError()

    def speech(
        self,
        text: str,
        language: str,
        on_done: Callable[[io.BytesIO], None],
        on_fail: Callable[[ProviderError], None],
    ):
        raise NotImplementedError()

    """
    Provider settings helpers and properties
    """

    @property
    def instance_url(self):
        return self.settings.get_string('instance-url') or self.defaults['instance_url']

    @instance_url.setter
    def instance_url(self, url):
        self.settings.set_string('instance-url', url)

    def reset_instance_url(self):
        self.instance_url = ''

    @property
    def api_key(self):
        return self.settings.get_string('api-key') or self.defaults['api_key']

    @api_key.setter
    def api_key(self, api_key):
        self.settings.set_string('api-key', api_key)

    def reset_api_key(self):
        self.api_key = ''

    @property
    def src_langs(self):
        return self.settings.get_strv('src-langs') or self.defaults['src_langs']

    @src_langs.setter
    def src_langs(self, src_langs):
        self.settings.set_strv('src-langs', src_langs)

    def reset_src_langs(self):
        self.src_langs = []

    @property
    def dest_langs(self):
        return self.settings.get_strv('dest-langs') or self.defaults['dest_langs']

    @dest_langs.setter
    def dest_langs(self, dest_langs):
        self.settings.set_strv('dest-langs', dest_langs)

    def reset_dest_langs(self):
        self.dest_langs = []

    """
    General provider helpers
    """

    @staticmethod
    def format_url(url: str, path: str = '', params: dict = {}, http: bool = False):
        """Formats a given url with path with the https protocol"""

        if not path.startswith('/'):
            path = '/' + path

        protocol = 'https://'
        if url.startswith('localhost:') or http:
            protocol = 'http://'

        params_str = urllib.parse.urlencode(params)
        if params_str:
            params_str = '?' + params_str

        return protocol + url + path + params_str

    def add_lang(self, original_code, name=None, trans=True, tts=False):
        """Add lang supported by provider"""

        code = normalize_lang_code(original_code)  # Get normalized lang code

        if trans:  # Add lang to supported languages list
            self.languages.append(code)
        if tts:  # Add lang to supported TTS languages list
            self.tts_languages.append(code)

        if code != original_code and code not in self._nonstandard_langs:
            # Save a divergent lang code for later denormalization
            self._nonstandard_langs[code] = original_code

        if name is not None and code not in self._languages_names:
            # Save name provider by the service
            self._languages_names[code] = name

    def denormalize_lang(self, *codes):
        """Get denormalized lang code if available"""

        if len(codes) == 1:
            return self._nonstandard_langs.get(codes[0], codes[0])

        result = []
        for code in codes:
            result.append(self._nonstandard_langs.get(code, code))
        return tuple(result)

    def get_lang_name(self, code):
        """Get language name"""
        name = get_lang_name(code)  # Try getting translated name from Dialect

        if name is None:  # Get name from provider if available
            return self._languages_names.get(code, code)

        return name
