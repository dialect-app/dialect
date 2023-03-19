# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import json
import logging
import urllib.parse

from gi.repository import GLib, Soup

from dialect.languages import get_lang_name, normalize_lang_code


class BaseProvider:
    __provider_type__ = ''
    """ The type of engine used by the provider
    str or dict if you want to use diferent engines per feature
    """
    name = ''
    """ Module name for itern use, like settings storing """
    prettyname = ''
    """ Module name for UI display """
    translation = False
    """ If it provides translation """
    tts = False
    """ If it provides text-to-speech """
    definitions = False
    """ If it provides dict definitions """
    change_instance = False
    """ If it supports changing the instance url """
    api_key_supported = False
    """ If it supports setting api keys """

    defaults = {
        'instance_url': '',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en']
    }

    def __init__(self, base_url='', api_key=''):
        self.instance_url = base_url
        self.api_key = api_key

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
        self.detection = False
        """ If it supports deteting text language (Auto translation) """
        self.mistakes = False
        """ If it supports showing translation mistakes """
        self.pronunciation = False
        """ If it supports showing translation pronunciation """
        self.suggestions = False
        """ If it supports sending translation suggestions to the service """
        self.api_key_required = False
        """ If the api key is required for the provider to work """
        self.history = []
        """ Here we save the translation history """

    @staticmethod
    def format_url(url: str, path: str = '', params: dict = {}, http: bool = False):
        """ Formats a given url with path with the https protocol """

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
        """ Add lang supported by provider """

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
        """ Get denormalized lang code if available """

        if len(codes) == 1:
            return self._nonstandard_langs.get(codes[0], codes[0])

        result = []
        for code in codes:
            result.append(self._nonstandard_langs.get(code, code))
        return tuple(result)

    def get_lang_name(self, code):
        """ Get language name """
        name = get_lang_name(code)  # Try getting translated name from Dialect

        if name is None:  # Get name from provider if available
            return self._languages_names.get(code, code)

        return name


class LocalProvider(BaseProvider):
    """ Base class for providers using the local threaded engine """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init_trans(self):
        pass

    def init_tts(self):
        pass

    def init_def(self):
        pass

    def translate(self, text: str, src: str, dest: str):
        pass

    def suggest(self, text: str, src: str, dest: str, suggestion: str) -> bool:
        pass

    def download_speech(self, text: str, language: str, file: io.BytesIO):
        pass


class SoupProvider(BaseProvider):
    """ Base class for providers using the libsoup engine """

    trans_init_requests = []
    """ List of request to do before using the provider """
    tts_init_requests = []
    """ List of request to do before using the provider """
    def_init_requests = []
    """ List of request to do before using the provider """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.error = ''
        """ Loading error when initializing """

    @staticmethod
    def encode_data(data) -> GLib.Bytes | None:
        """ Convert dict to JSON and bytes """
        data_glib_bytes = None
        try:
            data_bytes = json.dumps(data).encode('utf-8')
            data_glib_bytes = GLib.Bytes.new(data_bytes)
        except Exception as exc:
            logging.warning(exc)
        return data_glib_bytes

    @staticmethod
    def read_data(data: bytes) -> dict:
        """ Get JSON data from bytes """
        return json.loads(
                data
            ) if data else {}

    @staticmethod
    def create_request(method: str, url: str, data={}, headers: dict = {}, form: bool = False) -> Soup.Message:
        """ Helper for creating Soup.Message """

        if form and data:
            form_data = Soup.form_encode_hash(data)
            message = Soup.Message.new_from_encoded_form(method, url, form_data)
        else:
            message = Soup.Message.new(method, url)
        if data and not form:
            data = SoupProvider.encode_data(data)
            message.set_request_body_from_bytes('application/json', data)
        if headers:
            for name, value in headers.items():
                message.get_request_headers().append(name, value)
        if 'User-Agent' not in headers:
            message.get_request_headers().append('User-Agent', 'Dialect App')
        return message

    @staticmethod
    def format_validate_instance(url: str) -> Soup.Message:
        pass

    @staticmethod
    def validate_instance(data: bytes) -> bool:
        pass

    def format_validate_api_key(self, api_key: str) -> Soup.Message:
        pass

    def validate_api_key(self, data: bytes):
        pass

    def format_translation(self, text: str, src: str, dest: str) -> Soup.Message:
        pass

    def get_translation(self, data: bytes):
        pass

    def format_suggestion(self, text: str, src: str, dest: str, suggestion: str) -> Soup.Message:
        pass

    def get_suggestion(self, data: bytes) -> bool:
        pass

    def format_speech(self, text: str, language: str) -> Soup.Message:
        pass

    def get_speech(self, data: bytes, file: io.BytesIO):
        pass


class ProviderError(Exception):
    """Base Exception for Translator related errors."""

    def __init__(self, cause, message='Translator Error'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.cause}'


class ApiKeyRequired(ProviderError):
    """Exception raised when API key is required."""

    def __init__(self, cause, message='API Key Required'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class InvalidApiKey(ProviderError):
    """Exception raised when an invalid API key is found."""

    def __init__(self, cause, message='Invalid API Key'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class InvalidLangCode(ProviderError):
    """Exception raised when an invalid lang code is sent."""

    def __init__(self, cause, message='Invalid Lang Code'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class BatchSizeExceeded(ProviderError):
    """Exception raised when the batch size limit has been exceeded."""

    def __init__(self, cause, message='Batch Size Exceeded'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class CharactersLimitExceeded(ProviderError):
    """Exception raised when the char limit has been exceeded."""

    def __init__(self, cause, message='Characters Limit Exceeded'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class ServiceLimitReached(ProviderError):
    """Exception raised when the service limit has been reached."""

    def __init__(self, cause, message='Service Limit Reached'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class TranslationError(ProviderError):
    """Exception raised when translation fails."""

    def __init__(self, cause, message='Translation has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class TextToSpeechError(ProviderError):
    """Exception raised when tts fails."""

    def __init__(self, cause, message='Text to Speech has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)


class Translation:
    text = None
    extra_data = {
        'possible-mistakes': None,
        'src-pronunciation': None,
        'dest-pronunciation': None,
    }

    def __init__(self, text, extra_data):
        self.text = text
        self.extra_data = extra_data
