# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from dialect.providers.base import (
    ApiKeyRequired, BatchSizeExceeded, CharactersLimitExceeded,
    InvalidLangCode, InvalidApiKey, ProviderError, SoupProvider, Translation,
    TranslationError
)


class Provider(SoupProvider):
    __provider_type__ = 'soup'

    name = 'libretranslate'
    prettyname = 'LibreTranslate'
    translation = True
    tts = False
    definitions = False
    change_instance = True
    api_key_supported = True
    defaults = {
        'instance_url': 'libretranslate.de',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en']
    }

    trans_init_requests = [
        'languages',
        'settings'
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 0
        self.detection = True
        self._api_key_supported = False  # For LT conditional api keys

    @staticmethod
    def format_validate_instance(url):
        url = Provider.format_url(url, '/spec')
        return Provider.create_request('GET', url)

    @staticmethod
    def validate_instance(data):
        data = Provider.read_data(data)
        valid = False

        if data and data is not None:
            valid = data['info']['title'] == 'LibreTranslate'

        return valid

    @property
    def frontend_settings_url(self):
        return self.format_url(self.instance_url, '/frontend/settings')

    @property
    def detect_url(self):
        return self.format_url(self.instance_url, '/detect')

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, '/languages')

    @property
    def suggest_url(self):
        return self.format_url(self.instance_url, '/suggest')

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, '/translate')

    def format_languages_init(self):
        return self.create_request('GET', self.lang_url)

    def languages_init(self, data):
        try:
            data = self.read_data(data)
            self._check_errors(data)
            for lang in data:
                self.languages.append(lang['code'])
        except Exception as exc:
            logging.warning(exc)
            self.error = str(exc)

    def format_settings_init(self):
        return self.create_request('GET', self.frontend_settings_url)

    def settings_init(self, data):
        try:
            data = self.read_data(data)
            self._check_errors(data)
            self.suggestions = data.get('suggestions', False)
            self._api_key_supported = data.get('apiKeys', False)
            self.api_key_required = data.get('keyRequired', False)
            self.chars_limit = data.get('charLimit', 0)
        except Exception as exc:
            logging.warning(exc)
            self.error = str(exc)

    def format_validate_api_key(self, api_key):
        data = {
            'q': 'hello',
            'source': 'en',
            'target': 'es',
            'api_key': api_key,
        }
        return self.create_request('POST', self.translate_url, data)

    def validate_api_key(self, data):
        self.get_translation(data)

    def format_translation(self, text, src, dest):
        data = {
            'q': text,
            'source': src,
            'target': dest,
        }
        if self.api_key and self._api_key_supported:
            data['api_key'] = self.api_key

        return self.create_request('POST', self.translate_url, data)

    def get_translation(self, data):
        data = self.read_data(data)
        self._check_errors(data)
        translation = Translation(
            data['translatedText'],
            {
                'possible-mistakes': None,
                'src-pronunciation': None,
                'dest-pronunciation': None,
            },
        )

        return (translation, None)

    def format_suggestion(self, text, src, dest, suggestion):
        data = {
            'q': text,
            'source': src,
            'target': dest,
            's': suggestion,
        }
        if self.api_key and self._api_key_supported:
            data['api_key'] = self.api_key

        return self.create_request('POST', self.suggest_url, data)

    def get_suggestion(self, data):
        self._check_errors(data)
        return data.get('success', False)

    def _check_errors(self, data):
        """Raises a proper Exception if an error is found in the data."""
        if not data:
            raise ProviderError('Request empty')
        if 'error' in data:
            error = data['error']

            if error == 'Please contact the server operator to obtain an API key':
                raise ApiKeyRequired(error)
            elif error == 'Invalid API key':
                raise InvalidApiKey(error)
            elif 'is not supported' in error:
                raise InvalidLangCode(error)
            elif 'exceeds text limit' in error:
                raise BatchSizeExceeded(error)
            elif 'exceeds character limit' in error:
                raise CharactersLimitExceeded(error)
            elif 'Cannot translate text' in error or 'format is not supported' in error:
                raise TranslationError(error)
            else:
                raise ProviderError(error)
