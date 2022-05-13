# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from gi.repository import Soup

from dialect.translators.basetrans import (
    ApiKeyRequired, BatchSizeExceeded, CharactersLimitExceeded,
    InvalidLangCode, InvalidApiKey, TranslatorBase, Translation,
    TranslationError, TranslatorError
)
from dialect.session import Session, ResponseEmpty


class Translator(TranslatorBase):
    name = 'libretranslate'
    prettyname = 'LibreTranslate'
    history = []
    languages = []
    chars_limit = 0
    supported_features = {
        'detection': True,
        'mistakes': False,
        'pronunciation': False,
        'change-instance': True,
        'suggestions': False,
        'api-key-supported': False,
        'api-key-required': False,
    }
    instance_url = 'libretranslate.pussthecat.org'
    api_key = ''

    validation_path = '/spec'
    api_test_path = '/translate'

    def __init__(self, callback, base_url=None, api_key='', **kwargs):
        def on_loaded():
            callback(self.langs_success and self.settings_success, self.error, self.network_error)

        def on_langs_response(session, result):
            try:
                data = Session.get_response(session, result)
                self._check_errors(data)
                for lang in data:
                    self.languages.append(lang['code'])
                self.langs_success = True
            except (TranslatorError, ResponseEmpty) as exc:
                logging.warning(exc)
                self.error = str(exc)
            except Exception as exc:
                logging.warning(exc)
                self.error = str(exc)
                self.network_error = True

        def on_settings_response(session, result):
            try:
                data = Session.get_response(session, result)
                self._check_errors(data)
                self.supported_features['suggestions'] = data.get('suggestions', False)
                self.supported_features['api-key-supported'] = data.get('apiKeys', False)
                self.supported_features['api-key-required'] = data.get('keyRequired', False)
                self.chars_limit = data.get('charLimit', 0)
                self.settings_success = True
            except (TranslatorError, ResponseEmpty) as exc:
                logging.warning(exc)
                self.error = str(exc)
            except Exception as exc:
                logging.warning(exc)
                self.error = str(exc)
                self.network_error = True

        self.langs_success = False
        self.settings_success = False
        self.network_error = False
        self.error = ''

        if base_url is not None:
            self.instance_url = base_url
        self.api_key = api_key

        lang_message = Soup.Message.new('GET', self.lang_url)
        settings_message = Soup.Message.new('GET', self._frontend_settings_url)

        Session.get().multiple(
            [
                [lang_message, on_langs_response],
                [settings_message, on_settings_response]
            ],
            on_loaded
        )

    @property
    def _frontend_settings_url(self):
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

    @staticmethod
    def validate_instance(data):
        valid = False

        if data and data is not None:
            valid = data['info']['title'] == 'LibreTranslate'

        return valid

    @staticmethod
    def format_api_key_test(api_key):
        data = {
            'q': 'hello',
            'source': 'en',
            'target': 'es',
            'api_key': api_key,
        }

        return (data, {})

    def format_suggestion(self, text, src, dest, suggestion):
        data = {
            'q': text,
            'source': src,
            'target': dest,
            's': suggestion,
        }
        if self.api_key:
            data['api_key'] = self.api_key

        return (data, {})

    def get_suggestion(self, data):
        self._check_errors(data)
        return data.get('success', False)

    def format_translation(self, text, src, dest):
        data = {
            'q': text,
            'source': src,
            'target': dest,
        }
        if self.api_key:
            data['api_key'] = self.api_key

        return ('POST', data, {}, False)

    def get_translation(self, data):
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

    def _check_errors(self, data):
        """Raises a proper Exception if an error is found in the data."""
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
                raise TranslatorError(error)
