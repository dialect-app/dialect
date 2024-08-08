# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import urllib.parse
from dataclasses import dataclass
from enum import Enum, Flag, auto
from typing import IO, Callable

from dialect.define import LANG_ALIASES
from dialect.languages import get_lang_name
from dialect.providers.settings import ProviderDefaults, ProviderSettings


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
    API_KEY_USAGE = auto()
    """ If the service reports api usage """
    DETECTION = auto()
    """ If it supports detecting text language (Auto translation) """
    MISTAKES = auto()
    """ If it supports showing translation mistakes """
    PRONUNCIATION = auto()
    """ If it supports showing translation pronunciation """
    SUGGESTIONS = auto()
    """ If it supports sending translation suggestions to the service """


class ProvideLangModel(Enum):
    STATIC = auto()
    """
    The provider populate its `src_languages` and `dest_languages` properties.
    The `cmp_langs` method will be used to decide if one code can be translated to another.
    """
    DYNAMIC = auto()
    """
    The provider only populate its `src_languages` property.
    The `dest_langs_for` method will be used to get possible destination codes for a code.
    """


class ProviderErrorCode(Enum):
    UNEXPECTED = auto()
    NETWORK = auto()
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

    def __init__(self, code: ProviderErrorCode, message: str = "") -> None:
        self.code = code  # Serves for quick error matching
        self.message = message  # More detailed error info if needed


@dataclass
class Translation:
    text: str
    original: tuple[str, str, str]
    detected: str | None = None
    mistakes: tuple[str | None, str | None] = (None, None)
    pronunciation: tuple[str | None, str | None] = (None, None)


class BaseProvider:
    name = ""
    """ Module name for code use, like settings storing """
    prettyname = ""
    """ Module name for UI display """
    capabilities: ProviderCapability | None = None
    """ Provider capabilities, translation, tts, etc """
    features: ProviderFeature = ProviderFeature.NONE
    """ Provider features """
    lang_model: ProvideLangModel = ProvideLangModel.STATIC
    """ Translation language model """

    defaults: ProviderDefaults = {
        "instance_url": "",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }
    """ Default provider settings """

    def __init__(self):
        self.src_languages: list[str] = []
        """ Source languages available for translating """
        self.dest_languages: list[str] = []
        """ Destination languages available for translating """
        self.tts_languages: list[str] = []
        """ Languages available for TTS """
        self._nonstandard_langs: dict[str, str] = {}
        """ Mapping of lang codes that differ with Dialect ones """
        self._languages_names: dict[str, str] = {}
        """ Names of languages provided by the service """

        self.chars_limit: int = -1
        """ Translation char limit """

        self.history: list[Translation] = []
        """ Here we save the translation history """

        # GSettings
        self.settings = ProviderSettings(self.name, self.defaults)

    """
    Providers API methods
    """

    def validate_instance(self, url: str, on_done: Callable[[bool], None], on_fail: Callable[[ProviderError], None]):
        """
        Validate an instance of the provider.

        Args:
            url: The instance URL to test, only hostname and tld, e.g. libretranslate.com, localhost
            on_done: Called when the validation is done, argument is the result of the validation
            on_fail: Called when there's a fail in the validation process
        """
        raise NotImplementedError()

    def validate_api_key(self, key: str, on_done: Callable[[bool], None], on_fail: Callable[[ProviderError], None]):
        """
        Validate an API key.

        Args:
            key: The API key to validate
            on_done: Called when the validation is done, argument is the result of the validation
            on_fail: Called when there's a fail in the validation process
        """
        raise NotImplementedError()

    def init_trans(self, on_done: Callable[[], None], on_fail: Callable[[ProviderError], None]):
        """
        Initializes the provider translation capabilities.

        Args:
            on_done: Called after the provider was successfully initialized
            on_fail: Called after any error on initialization
        """
        on_done()

    def init_tts(self, on_done: Callable[[], None], on_fail: Callable[[ProviderError], None]):
        """
        Initializes the provider text-to-speech capabilities.

        Args:
            on_done: Called after the provider was successfully initialized
            on_fail: Called after any error on initialization
        """
        on_done()

    def translate(
        self,
        text: str,
        src: str,
        dest: str,
        on_done: Callable[[Translation], None],
        on_fail: Callable[[ProviderError], None],
    ):
        """
        Translates text in the provider.

        Args:
            text: The text to translate
            src: The lang code of the source text
            dest: The lang code to translate the text to
            on_done: Called after the text was successfully translated
            on_fail: Called after any error on translation
        """
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
        """
        Sends a translation suggestion to the provider.

        Args:
            text: Original text without translation
            src: The lang code of the original text
            dest: The lang code of the translated text
            suggestion: Suggested translation for text
            on_done: Called after the suggestion was successfully send, argument means if it was accepted or rejected
            on_fail: Called after any error on the suggestion process
        """
        raise NotImplementedError()

    def speech(
        self,
        text: str,
        language: str,
        on_done: Callable[[IO], None],
        on_fail: Callable[[ProviderError], None],
    ):
        """
        Generate speech audio from text

        Args:
            text: Text to generate speech from
            language: The lang code of text
            on_done: Called after the process successful
            on_fail: Called after any error on the speech process
        """
        raise NotImplementedError()

    def api_char_usage(
        self,
        on_done: Callable[[int, int], None],
        on_fail: Callable[[ProviderError], None],
    ):
        """
        Retrieves the API usage status

        Args:
            on_done: Called after the process successful, with the usage and limit as args
            on_fail: Called after any error on the speech process
        """
        raise NotImplementedError()

    def cmp_langs(self, a: str, b: str) -> bool:
        """
        Compare two language codes.

        It assumes that the codes have been normalized by `normalize_lang_code`.

        This method exists so providers can add additional comparison logic.

        Args:
            a: First lang to compare
            b: Second lang to compare
        """

        return a == b

    def dest_langs_for(self, code: str) -> list[str]:
        """
        Get the available destination languages for a source language.
        """
        raise NotImplementedError()

    @property
    def lang_aliases(self) -> dict[str, str]:
        """
        Mapping of Dialect/CLDR's lang codes to the provider ones.

        Some providers might use different lang codes from the ones used by Dialect to for example get localized
        language names.

        This dict is used by `add_lang` so lang codes can later be denormalized with `denormalize_lang`.

        Codes must be formatted with the criteria from normalize_lang_code, because this value would be used by
        `add_lang` after normalization.

        Check `dialect.define.LANG_ALIASES` for reference mappings.
        """
        return {}

    """
    Provider settings helpers and properties
    """

    @property
    def instance_url(self) -> str:
        """Instance url saved on settings."""
        return self.settings.instance_url

    @instance_url.setter
    def instance_url(self, url: str):
        self.settings.instance_url = url

    def reset_instance_url(self):
        """Resets saved instance url."""
        self.instance_url = ""

    @property
    def api_key(self) -> str:
        """API key saved on settings."""
        return self.settings.api_key

    @api_key.setter
    def api_key(self, api_key: str):
        self.settings.api_key = api_key

    def reset_api_key(self):
        """Resets saved API key."""
        self.api_key = ""

    @property
    def recent_src_langs(self) -> list[str]:
        """Saved recent source langs of the user."""
        return self.settings.src_langs

    @recent_src_langs.setter
    def recent_src_langs(self, src_langs: list[str]):
        self.settings.src_langs = src_langs

    def reset_src_langs(self):
        """Reset saved recent user source langs"""
        self.recent_src_langs = []

    @property
    def recent_dest_langs(self) -> list[str]:
        """Saved recent destination langs of the user."""
        return self.settings.dest_langs

    @recent_dest_langs.setter
    def recent_dest_langs(self, dest_langs: list[str]):
        self.settings.dest_langs = dest_langs

    def reset_dest_langs(self):
        """Reset saved recent user destination langs"""
        self.recent_dest_langs = []

    """
    General provider helpers
    """

    @staticmethod
    def format_url(url: str, path: str = "", params: dict = {}, http: bool = False):
        """
        Compose a HTTP url with the given pieces.

        If url is localhost, `http` is ignored and HTTP protocol is forced.

        Args:
            url: Base url, hostname and tld
            path: Path of the url
            params: Params to populate a url query
            http: If HTTP should be used instead of HTTPS
        """

        if not path.startswith("/"):
            path = "/" + path

        protocol = "https://"
        if url.startswith("localhost:") or http:
            protocol = "http://"

        params_str = urllib.parse.urlencode(params)
        if params_str:
            params_str = "?" + params_str

        return protocol + url + path + params_str

    def normalize_lang_code(self, code: str):
        """
        Normalice a language code to Dialect's criteria.

        Criteria:
        - Codes must be lowercase, e.g. ES => es
        - Codes can have a second code delimited by a hyphen, e.g. zh_CN => zh-CN
        - If second code is two chars long it's considered a country code and must be uppercase, e.g. zh-cn => zh-CN
        - If second code is four chars long it's considered a script code and must be capitalized,
        e.g. zh-HANS => zh-Hans

        This method also maps lang codes aliases using `lang_aliases` and `dialect.define.LANG_ALIASES`.

        Args:
            code: Language ISO code
        """
        code = code.replace("_", "-").lower()  # Normalize separator
        codes = code.split("-")

        if len(codes) == 2:  # Code contain a script or country code
            if len(codes[1]) == 4:  # ISO 15924 (script)
                codes[1] = codes[1].capitalize()

            elif len(codes[1]) == 2:  # ISO 3166-1 (country)
                codes[1] = codes[1].upper()

            code = "-".join(codes)

        aliases = {**LANG_ALIASES, **self.lang_aliases}
        if code in aliases:
            code = aliases[code]

        return code

    def add_lang(
        self,
        original_code: str,
        name: str | None = None,
        trans_src: bool = True,
        trans_dest: bool = True,
        tts: bool = False,
    ):
        """
        Add lang supported by provider after normalization.

        Normalized lang codes are saved for latter denormalization using `denormalize_lang`.

        Args:
            original_code: Lang code to add
            name: Language name to fallback in case Dialect doesn't provide one
            trans_src: Add language as supported for translation as src
            trans_dest: Add language as supported for translation as dest
            tts: Add language as supported for text-to-speech
        """

        code = self.normalize_lang_code(original_code)  # Get normalized lang code

        if trans_src:  # Add lang to supported languages list
            self.src_languages.append(code)
        if trans_dest:
            self.dest_languages.append(code)
        if tts:  # Add lang to supported TTS languages list
            self.tts_languages.append(code)

        if code != original_code and code not in self._nonstandard_langs:
            # Save a divergent lang code for later denormalization
            self._nonstandard_langs[code] = original_code

        if name is not None and code not in self._languages_names:
            # Save name provider by the service
            self._languages_names[code] = name

    def denormalize_lang(self, *codes: str) -> str | tuple[str, ...]:
        """
        Get denormalized lang code if available.

        This method will return a tuple with the same length of given codes or a str if only one code was passed.

        Args:
        *codes: Lang codes to denormalize
        """

        if len(codes) == 1:
            return self._nonstandard_langs.get(codes[0], codes[0])

        result = []
        for code in codes:
            result.append(self._nonstandard_langs.get(code, code))
        return tuple(result)

    def get_lang_name(self, code: str) -> str | None:
        """
        Get a localized language name.

        Fallback to a name provided by the provider if available or ultimately just the code.

        Args:
            code: Language to get a name for
        """
        name = get_lang_name(code)  # Try getting translated name from Dialect

        if name is None:  # Get name from provider if available
            return self._languages_names.get(code, code)

        return name
