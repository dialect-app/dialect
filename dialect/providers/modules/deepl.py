# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    ProviderErrorCode,
    ProviderError,
    Translation,
)
from dialect.providers.soup import SoupProvider

API_V = "v2"


class Provider(SoupProvider):
    name = 'deepl'
    prettyname = 'DeepL'

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.DETECTION | ProviderFeature.API_KEY | ProviderFeature.API_KEY_REQUIRED

    defaults = {
        # TODO: Do we want to support pro users?
        'instance_url': 'api-free.deepl.com',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en'],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = -1  # TODO: What is the limit?

    @property
    def lang_url(self):
        # TODO: we need to extend the providers API to allow different src/dest lang lists
        return self.format_url(self.instance_url, f'/{API_V}/languages', {'type': 'target'})

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, f'/{API_V}/translate')

    @property
    def headers(self):
        return {'Authorization': f'DeepL-Auth-Key {self.api_key}'}

    def init_trans(self, on_done, on_fail):
        def on_response(data):
            try:
                for lang in data:
                    self.add_lang(lang['language'], lang['name'])

                on_done()

            except Exception as exc:
                logging.warning(exc)
                on_fail(ProviderError(ProviderErrorCode.UNEXPECTED, str(exc)))

        # Request messages
        languages_message = self.create_message('GET', self.lang_url, headers=self.headers)
        # Do async requests
        self.send_and_read_and_process_response(languages_message, on_response, on_fail)

    def validate_api_key(self, key, on_done, on_fail):
        def on_response(_data):
            valid = languages_message.get_status() == 200
            on_done(valid)

        # TODO: Is there a better endpoint for checking auth?
        # Headers
        headers = {'Authorization': f'DeepL-Auth-Key {key}'}
        # Request messages
        languages_message = self.create_message('GET', self.lang_url, headers=headers)
        # Do async requests
        self.send_and_read_and_process_response(languages_message, on_response, on_fail)

    def translate(self, text, src, dest, on_done, on_fail):
        def on_response(data):
            try:
                translations = data.get('translations')
                detected = translations[0].get('detected_source_language')
                translation = Translation(translations[0]['text'], (text, src, dest), detected)
                on_done(translation)

            except Exception as exc:
                logging.warning(exc)
                on_fail(ProviderError(ProviderErrorCode.TRANSLATION_FAILED, str(exc)))

        # Request body
        data = {
            'text': [text],
            'target_lang': dest,
        }
        if src != 'auto':
            data['source_lang'] = src

        # Request message
        message = self.create_message('POST', self.translate_url, data, self.headers)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def check_known_errors(self, status, data):
        message = data.get('message', '') if isinstance(data, dict) else ''

        match status:
            case 403:
                if not self.api_key:
                    return ProviderError(ProviderErrorCode.API_KEY_REQUIRED, message)
                return ProviderError(ProviderErrorCode.API_KEY_INVALID, message)
            case 456:
                return ProviderError(ProviderErrorCode.SERVICE_LIMIT_REACHED, message)

        if status != 200:
            return ProviderError(ProviderErrorCode.UNEXPECTED, message)
